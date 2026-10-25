"""`POST /v1/billing/checkout` + `POST /v1/billing/webhook` (Phase 7).

The webhook route is deliberately public — Stripe authenticates itself via
`verify_webhook_signature()`, not a bearer token, so this reads the raw
request body directly rather than taking a parsed Pydantic model (signature
verification needs the exact bytes Stripe signed). An unrecognized event,
another NEXORA product's subscription on the shared Stripe account, or an
account that doesn't exist yet all return `200`/no-op rather than an error
— a non-2xx makes Stripe retry for days and eventually disable the
endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

from vigilo_api.audit_log import record
from vigilo_api.deps import AccountDep, ActiveOrgDep, SessionDep
from vigilo_api.schemas import (
    BillingProductLine,
    BillingSummaryResponse,
    BillingTotals,
    CheckoutRequest,
    CheckoutResponse,
    PlanResponse,
    PortalResponse,
)
from vigilo_billing import PLANS, PlanId, UnrecognizedWebhookEvent, interpret_webhook_event
from vigilo_core.config import config
from vigilo_identity.org_repository import (
    PRODUCT_SLUGS,
    get_org,
    personal_org_id,
    plan_id_for_org,
)
from vigilo_identity.repository import (
    get_account_by_email,
    get_account_by_id,
    get_subscription_for_org,
    subscription_event_is_stale,
    upsert_subscription,
)
from vigilo_integrations.billing import (
    create_checkout_url,
    create_portal_url,
    parse_webhook_event,
    price_to_plan,
    verify_webhook_signature,
)
from vigilo_security.audit import AuditEvent, audit

router = APIRouter(prefix="/v1/billing", tags=["billing"])

# A separate router (bare /v1 prefix, not /v1/billing) for GET /v1/plans —
# the dashboard's billing/upgrade page's plan-comparison data. Genuinely
# public: no account, no session, just the static in-memory PLANS dict.
plans_router = APIRouter(prefix="/v1", tags=["billing"])


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest, account: AccountDep, org: ActiveOrgDep, session: SessionDep
) -> CheckoutResponse:
    """Subscribe the *active organisation* (owner or admin). The organisation,
    not the caller, owns the subscription and the Stripe customer."""
    org.require("admin")
    if body.product_slug != "vigilo":
        raise HTTPException(status_code=422, detail="that product cannot be bought yet")
    if await plan_id_for_org(session, org.org_id, body.product_slug) is not None:
        raise HTTPException(
            status_code=409,
            detail="this organisation already has a plan; use the billing portal to change it",
        )

    organization = await get_org(session, org.org_id)
    billing_page = f"{config().web_app_url or ''}/dashboard/billing"
    checkout_url = await create_checkout_url(
        body.plan_id,
        account.email,
        str(account.id),
        success_url=f"{billing_page}?checkout=success",
        cancel_url=billing_page,
        interval=body.interval,
        org_id=str(org.org_id),
        customer_id=organization.billing_customer_id if organization else None,
    )
    await record(
        session,
        account,
        org.org_id,
        "checkout_started",
        body.plan_id,
        product=body.product_slug,
        interval=body.interval,
    )
    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal")
async def create_portal(
    account: AccountDep, org: ActiveOrgDep, session: SessionDep
) -> PortalResponse:
    """Self-service subscription management (cancel, card, invoices) on
    Stripe's hosted Customer Portal, scoped to the active organisation's own
    latest Stripe subscription — never one named by the client."""
    org.require("admin")
    subscription = await get_subscription_for_org(session, org.org_id)
    if subscription is not None and subscription.provider == "nexora-core":
        # NEXORA Core bills this organisation; it is managed there, not on Vigilo's portal.
        raise HTTPException(
            status_code=409,
            detail=f"billing for this organisation is managed in NEXORA Console: "
            f"{config().nexora_console_billing_url}",
        )
    if subscription is None or subscription.provider != "stripe":
        raise HTTPException(status_code=404, detail="no subscription to manage")

    portal_url = await create_portal_url(
        subscription.provider_subscription_id,
        return_url=f"{config().web_app_url or ''}/dashboard/billing",
    )
    await record(session, account, org.org_id, "billing_portal_opened", "stripe")
    return PortalResponse(portal_url=portal_url)


# Display names for every product; only Vigilo can be bought so far.
_PRODUCT_NAMES = {
    "vigilo": "Vigilo",
    "sentinel": "Sentinel",
    "cspm": "CSPM",
    "gateway": "Gateway",
    "neurawall": "NeuraWall",
}
_PURCHASABLE = frozenset({"vigilo"})


def _plan_or_none(plan_id: str):
    try:
        return PLANS[PlanId(plan_id)]
    except (ValueError, KeyError):
        return None


@router.get("/summary")
async def billing_summary(org: ActiveOrgDep, session: SessionDep) -> BillingSummaryResponse:
    """What the active organisation pays for, across every product, on one
    screen. Owners and admins only: it shows prices and renewal dates."""
    org.require("admin")
    organization = await get_org(session, org.org_id)
    lines: list[BillingProductLine] = []
    monthly = yearly = 0
    for slug in PRODUCT_SLUGS:
        sub = await get_subscription_for_org(session, org.org_id, slug)
        if sub is not None and sub.status == "active":
            plan = _plan_or_none(sub.plan_id)
            interval = "year" if sub.billing_interval == "year" else "month"
            amount = 0
            if plan is not None:
                amount = plan.price_cents_yearly if interval == "year" else plan.price_cents
            if interval == "year":
                yearly += amount
            else:
                monthly += amount
            lines.append(
                BillingProductLine(
                    product_slug=slug,
                    product_name=_PRODUCT_NAMES[slug],
                    plan_id=sub.plan_id,
                    status="active",
                    interval=interval,
                    amount_cents=amount,
                    current_period_end=sub.current_period_end,
                    cancel_at_period_end=sub.cancel_at_period_end,
                    can_purchase=slug in _PURCHASABLE,
                )
            )
        else:
            lines.append(
                BillingProductLine(
                    product_slug=slug,
                    product_name=_PRODUCT_NAMES[slug],
                    plan_id="free",
                    status="free",
                    amount_cents=0,
                    can_purchase=slug in _PURCHASABLE,
                )
            )
    return BillingSummaryResponse(
        org_id=org.org_id,
        org_name=organization.name if organization else "",
        products=lines,
        totals=BillingTotals(monthly_cents=monthly, yearly_cents=yearly),
    )


@plans_router.get("/plans")
async def list_plans() -> list[PlanResponse]:
    return [PlanResponse.model_validate(plan) for plan in PLANS.values()]


@router.post("/webhook")
async def receive_webhook(request: Request, session: SessionDep) -> dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    payload = parse_webhook_event(raw_body)

    try:
        event = interpret_webhook_event(payload, price_to_plan())
    except UnrecognizedWebhookEvent:
        return {"status": "ignored"}

    # Which organisation pays: the one named at checkout, else (subscriptions
    # made before organisations) the paying account's personal organisation.
    account = None
    if event.account_id:
        try:
            account = await get_account_by_id(session, uuid.UUID(event.account_id))
        except ValueError:
            account = None
    if account is None:
        account = await get_account_by_email(session, event.account_email)

    org_id: uuid.UUID | None = None
    if event.org_id:
        try:
            org = await get_org(session, uuid.UUID(event.org_id))
        except ValueError:
            org = None
        if org is None:
            return {"status": "ignored"}
        org_id = org.id
        if account is None:
            account = await get_account_by_id(session, org.created_by)
    if account is None:
        return {"status": "ignored"}

    if await subscription_event_is_stale(
        session, event.provider_subscription_id, event.event_created
    ):
        return {"status": "stale"}

    await upsert_subscription(
        session,
        account_id=account.id,
        plan_id=event.plan_id,
        status=event.status,
        provider=event.provider,
        provider_subscription_id=event.provider_subscription_id,
        current_period_end=event.period_end,
        org_id=org_id,
        billing_interval=event.interval,
        customer_id=event.customer_id,
        event_created=event.event_created,
        cancel_at_period_end=event.cancel_at_period_end,
    )
    await audit(
        session,
        AuditEvent(
            actor="stripe",
            action="subscription_updated",
            subject=event.provider_subscription_id,
            account_id=account.id,
            org_id=org_id or await personal_org_id(session, account.id),
            metadata={
                "plan_id": event.plan_id,
                "status": event.status,
                "org_id": str(org_id) if org_id else None,
            },
        ),
    )

    return {"status": "applied"}
