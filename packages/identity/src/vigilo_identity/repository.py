"""Account repository. Every function takes an already-open `AsyncSession`
rather than opening its own — the caller (an API handler or ARQ job body,
via `vigilo_persistence.session_scope`) controls the transaction boundary,
matching the pattern `vigilo_security.audit.audit()` uses for the same reason
(ADR-0003: a decision and everything it depends on commit together).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vigilo_identity.models import Account, ApiKey, BrandingProfile, Subscription
from vigilo_identity.org_repository import OrgError, create_org, personal_org_id
from vigilo_identity.orm import (
    AccountRow,
    ApiKeyRow,
    BrandingProfileRow,
    CoreOrgPlanRow,
    MembershipRow,
    OrganizationRow,
    SubscriptionRow,
)


async def get_account_by_id(session: AsyncSession, account_id: object) -> Account | None:
    row = await session.get(AccountRow, account_id)
    return Account.model_validate(row) if row else None


async def get_account_by_clerk_id(session: AsyncSession, clerk_user_id: str) -> Account | None:
    stmt = select(AccountRow).where(AccountRow.clerk_user_id == clerk_user_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return Account.model_validate(row) if row else None


async def get_account_by_email(session: AsyncSession, email: str) -> Account | None:
    """Read-only — never creates. Used where a caller needs to know whether
    a *returning* submitter already exists without the side effect of
    `get_or_create_account`, e.g. `POST /v1/scans` looking up a returning
    submitter's real verification state before deciding whether a denied
    request should be allowed to leave no account/target row behind."""
    stmt = select(AccountRow).where(AccountRow.email == email)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return Account.model_validate(row) if row else None


async def get_or_create_account(
    session: AsyncSession, email: str, clerk_user_id: str | None = None
) -> Account:
    """Look up an account by email; create one if none exists.

    If a Clerk id is supplied and the matching-by-email row is still
    anonymous (created earlier by a free scan, never signed in), attach the
    Clerk id and promote it to `active` in place — this is what makes the
    anonymous free-scan path (exit criterion a) and the authenticated
    ownership-verification path (exit criterion b) converge on one `Account`
    row rather than creating a duplicate the day someone signs up.
    """
    result = await session.execute(select(AccountRow).where(AccountRow.email == email))
    row = result.scalar_one_or_none()

    if row is None:
        try:
            # Savepoint: two requests can arrive for a brand-new person at once
            # (a page and its layout both call the API on first load). The
            # unique constraints pick one winner; the loser reads its row back.
            async with session.begin_nested():
                row = AccountRow(
                    email=email,
                    clerk_user_id=clerk_user_id,
                    status="active" if clerk_user_id else "anonymous",
                )
                session.add(row)
                await session.flush()
            return Account.model_validate(row)
        except IntegrityError:
            match = AccountRow.email == email
            if clerk_user_id:
                match = or_(match, AccountRow.clerk_user_id == clerk_user_id)
            row = (await session.execute(select(AccountRow).where(match))).scalars().first()
            if row is None:
                raise

    if clerk_user_id and row.clerk_user_id is None:
        row.clerk_user_id = clerk_user_id
        row.status = "active"
        await session.flush()

    return Account.model_validate(row)


async def get_subscription_by_account(
    session: AsyncSession, account_id: uuid.UUID
) -> Subscription | None:
    """The most recent subscription row for this account, if more than one
    exists — a provider issues a new `provider_subscription_id` on plan
    change/renewal, so rows accumulate over time rather than being
    updated in place."""
    stmt = (
        select(SubscriptionRow)
        .where(SubscriptionRow.account_id == account_id)
        .order_by(SubscriptionRow.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return Subscription.model_validate(row) if row else None


async def subscription_event_is_stale(
    session: AsyncSession, provider_subscription_id: str, event_created: datetime | None
) -> bool:
    """Webhook delivery is not ordered: an event older than the last one
    applied to the same subscription must not roll its state back."""
    if event_created is None:
        return False
    result = await session.execute(
        select(SubscriptionRow.provider_event_created).where(
            SubscriptionRow.provider_subscription_id == provider_subscription_id
        )
    )
    last = result.scalar_one_or_none()
    return last is not None and event_created < last


CORE_PROVIDER = "nexora-core"


async def apply_core_plan(session: AsyncSession, org: OrganizationRow, plan_id: str) -> None:
    """Idempotent: one subscription row per organisation, keyed `nexora-core:<org id>`;
    `free` closes it, anything else opens it. `account_id` is the organisation's creator,
    who stands in for "who paid"."""
    paid = plan_id != "free"
    await upsert_subscription(
        session,
        org.created_by,
        plan_id,
        "active" if paid else "canceled",
        CORE_PROVIDER,
        f"{CORE_PROVIDER}:{org.id}",
        None,
        org_id=org.id,
    )


async def set_org_plan_from_core(
    session: AsyncSession, clerk_org_id: str, plan_id: str
) -> OrganizationRow | None:
    """NEXORA Core owns the subscription of an organisation it bills and tells us the
    resulting plan. Always remembers it, then applies it to the organisation linked to
    that Clerk organisation (`organizations.clerk_org_id`). Returns None when none is
    linked yet; the remembered plan is applied when one is (`link_clerk_org`)."""
    await session.execute(
        pg_insert(CoreOrgPlanRow)
        .values(clerk_org_id=clerk_org_id, plan_id=plan_id)
        .on_conflict_do_update(
            index_elements=["clerk_org_id"], set_={"plan_id": plan_id, "updated_at": func.now()}
        )
    )
    result = await session.execute(
        select(OrganizationRow).where(OrganizationRow.clerk_org_id == clerk_org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        return None
    await apply_core_plan(session, org, plan_id)
    return org


_CLERK_ROLES = {"org:admin": "admin", "org:member": "member"}


async def link_clerk_org(
    session: AsyncSession,
    account: Account,
    clerk_org_id: str,
    clerk_role: str | None,
    name: str | None = None,
) -> tuple[OrganizationRow, str]:
    """ADR-0014 phase 2: the caller's Clerk token names an organisation. Returns the Vigilo
    organisation linked to it and the caller's role there, creating both when needed.

    Only a Clerk organisation admin may create the link (the creator becomes owner); anyone
    else must wait for one to open Vigilo first (`OrgError("not_linked")`). A member is
    added with the role Clerk gives them (`org:admin` admin, anything else member), and an
    owner's role is never changed by a token. The plan Core last sent for the organisation
    is applied when it is first linked. Removing someone in Clerk does not remove their
    membership here (their token just stops naming the organisation)."""
    mapped = _CLERK_ROLES.get(clerk_role or "", "member")
    result = await session.execute(
        select(OrganizationRow).where(OrganizationRow.clerk_org_id == clerk_org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        if mapped != "admin":
            raise OrgError(
                "not_linked", "an organisation admin must open Vigilo first to set it up"
            )
        slug = f"clerk-{clerk_org_id.removeprefix('org_').lower()}"[:48]
        try:
            async with session.begin_nested():
                created = await create_org(session, account, (name or "Team workspace")[:200], slug)
                row = await session.get(OrganizationRow, created.id)
                assert row is not None
                row.clerk_org_id = clerk_org_id
                await session.flush()
        except (OrgError, IntegrityError):
            # Two first requests raced; read back the winner's row.
            result = await session.execute(
                select(OrganizationRow).where(OrganizationRow.clerk_org_id == clerk_org_id)
            )
            row = result.scalar_one()
        org = row
        pending = await session.get(CoreOrgPlanRow, clerk_org_id)
        if pending is not None:
            await apply_core_plan(session, org, pending.plan_id)

    result = await session.execute(
        select(MembershipRow).where(
            MembershipRow.org_id == org.id, MembershipRow.account_id == account.id
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        membership = MembershipRow(org_id=org.id, account_id=account.id, role=mapped)
        session.add(membership)
        await session.flush()
    elif membership.role != "owner" and membership.role != mapped:
        membership.role = mapped
        await session.flush()
    return org, membership.role


async def list_clerk_linked_orgs(session: AsyncSession) -> list[OrganizationRow]:
    result = await session.execute(
        select(OrganizationRow).where(OrganizationRow.clerk_org_id.is_not(None))
    )
    return list(result.scalars())


async def remove_members_missing_from_clerk(
    session: AsyncSession, org: OrganizationRow, clerk_user_ids: set[str]
) -> list[AccountRow]:
    """ADR-0014: a Clerk-linked organisation's membership follows Clerk. Removes the
    non-owner members whose Clerk user is not in `clerk_user_ids` and returns their accounts.
    Owners are never removed here (an owner who left Clerk needs a person to decide), and an
    empty list removes nobody: it more likely means a bad answer than an empty organisation."""
    if not clerk_user_ids:
        return []
    result = await session.execute(
        select(MembershipRow, AccountRow)
        .join(AccountRow, AccountRow.id == MembershipRow.account_id)
        .where(MembershipRow.org_id == org.id, MembershipRow.role != "owner")
    )
    removed: list[AccountRow] = []
    for membership, account in result.all():
        if account.clerk_user_id in clerk_user_ids:
            continue
        await session.delete(membership)
        removed.append(account)
    await session.flush()
    return removed


async def upsert_subscription(
    session: AsyncSession,
    account_id: uuid.UUID,
    plan_id: str,
    status: str,
    provider: str,
    provider_subscription_id: str,
    current_period_end: datetime | None,
    *,
    org_id: uuid.UUID | None = None,
    product_slug: str = "vigilo",
    billing_interval: str = "month",
    customer_id: str | None = None,
    event_created: datetime | None = None,
    cancel_at_period_end: bool = False,
) -> Subscription:
    """A subscription belongs to an organisation (default: `account_id`'s
    personal one) and a product; `account_id` is who paid. Keyed on
    `provider_subscription_id` — a webhook replaying the same event, or a later
    status update for the same subscription, updates the existing row rather
    than creating a duplicate. For a *personal* organisation the same flush
    also sets `AccountRow.plan_id`, the legacy per-account view `/v1/me` still
    reads; a team organisation's plan lives only here, on its subscription
    (`vigilo_identity.org_repository.plan_id_for_org`). `customer_id` is the
    provider's customer, remembered on the organisation so its next checkout
    reuses it."""
    org_id = org_id or await personal_org_id(session, account_id)
    result = await session.execute(
        select(SubscriptionRow).where(
            SubscriptionRow.provider_subscription_id == provider_subscription_id
        )
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = SubscriptionRow(
            account_id=account_id,
            org_id=org_id,
            product_slug=product_slug,
            billing_interval=billing_interval,
            plan_id=plan_id,
            status=status,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            current_period_end=current_period_end,
            provider_event_created=event_created,
            cancel_at_period_end=cancel_at_period_end,
        )
        session.add(row)
    else:
        row.plan_id = plan_id
        row.status = status
        row.current_period_end = current_period_end
        row.billing_interval = billing_interval
        row.cancel_at_period_end = cancel_at_period_end
        if event_created is not None:
            row.provider_event_created = event_created

    org_row = await session.get(OrganizationRow, org_id)
    if org_row is not None:
        if customer_id and org_row.billing_customer_id is None:
            org_row.billing_customer_id = customer_id
        # A canceled/non-active subscription must NOT leave the account
        # holding paid entitlements forever, so a personal organisation's
        # cancellation resets the legacy account plan to "free".
        if org_row.is_personal and product_slug == "vigilo":
            account_row = await session.get(AccountRow, org_row.created_by)
            if account_row is not None:
                account_row.plan_id = plan_id if status == "active" else "free"

    await session.flush()
    return Subscription.model_validate(row)


async def get_subscription_for_org(
    session: AsyncSession, org_id: uuid.UUID, product_slug: str = "vigilo"
) -> Subscription | None:
    """The organisation's most recent subscription for a product, any status."""
    stmt = (
        select(SubscriptionRow)
        .where(SubscriptionRow.org_id == org_id, SubscriptionRow.product_slug == product_slug)
        .order_by(SubscriptionRow.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return Subscription.model_validate(row) if row else None


def hash_api_key(raw_key: str) -> str:
    """The one place a presented API key is turned into its lookup hash —
    `create_api_key()` below and `apps/api`'s verification-time lookup
    both call this, so there is exactly one hashing implementation to keep
    in sync. Matches `vigilo_orchestrator.reports`'s own share-link
    token-hashing precedent, made public here since hashing and lookup
    live in different packages for API keys (creation in `apps/api`'s
    session-authenticated router, verification in its API-key auth
    dependency)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def create_api_key(
    session: AsyncSession,
    account_id: uuid.UUID,
    name: str,
    scopes: list[str],
    org_id: uuid.UUID | None = None,
) -> tuple[ApiKey, str]:
    """Returns `(api_key, plaintext_key)` — the plaintext is returned
    exactly once, at creation, and never persisted (`key_hash` only),
    matching `create_share_link()`'s exact token pattern. The key belongs to
    `org_id` (default: the creator's personal org), so it survives its
    creator leaving the organisation."""
    raw_key = f"vglo_{secrets.token_urlsafe(32)}"
    row = ApiKeyRow(
        account_id=account_id,
        org_id=org_id or await personal_org_id(session, account_id),
        name=name,
        prefix=raw_key[:12],
        key_hash=hash_api_key(raw_key),
        scopes=scopes,
    )
    session.add(row)
    await session.flush()
    return ApiKey.model_validate(row), raw_key


async def get_api_key_by_hash(session: AsyncSession, key_hash: str) -> ApiKey | None:
    result = await session.execute(select(ApiKeyRow).where(ApiKeyRow.key_hash == key_hash))
    row = result.scalar_one_or_none()
    return ApiKey.model_validate(row) if row else None


async def list_api_keys_for_account(session: AsyncSession, account_id: uuid.UUID) -> list[ApiKey]:
    result = await session.execute(
        select(ApiKeyRow)
        .where(ApiKeyRow.account_id == account_id)
        .order_by(ApiKeyRow.created_at.desc())
    )
    return [ApiKey.model_validate(row) for row in result.scalars().all()]


async def list_api_keys_for_org(session: AsyncSession, org_id: uuid.UUID) -> list[ApiKey]:
    result = await session.execute(
        select(ApiKeyRow).where(ApiKeyRow.org_id == org_id).order_by(ApiKeyRow.created_at.desc())
    )
    return [ApiKey.model_validate(row) for row in result.scalars().all()]


async def count_api_keys_for_org(session: AsyncSession, org_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(ApiKeyRow)
        .where(ApiKeyRow.org_id == org_id, ApiKeyRow.revoked_at.is_(None))
    )
    return result.scalar_one()


async def revoke_api_key(session: AsyncSession, api_key_id: uuid.UUID) -> ApiKey | None:
    row = await session.get(ApiKeyRow, api_key_id)
    if row is None:
        return None
    row.revoked_at = datetime.now(UTC)
    await session.flush()
    return ApiKey.model_validate(row)


async def mark_api_key_used(
    session: AsyncSession, api_key_id: uuid.UUID, used_at: datetime
) -> None:
    row = await session.get(ApiKeyRow, api_key_id)
    if row is not None:
        row.last_used_at = used_at
        await session.flush()


async def count_api_keys_for_account(session: AsyncSession, account_id: uuid.UUID) -> int:
    """Feeds `vigilo_billing.consume(..., Meter.API_KEYS, ...)` — a live
    `COUNT` of non-revoked keys, matching `count_monitors_for_account`'s
    precedent."""
    result = await session.execute(
        select(func.count())
        .select_from(ApiKeyRow)
        .where(ApiKeyRow.account_id == account_id, ApiKeyRow.revoked_at.is_(None))
    )
    return result.scalar_one()


async def get_branding_profile_for_org(
    session: AsyncSession, org_id: uuid.UUID
) -> BrandingProfile | None:
    result = await session.execute(
        select(BrandingProfileRow).where(BrandingProfileRow.org_id == org_id)
    )
    row = result.scalar_one_or_none()
    return BrandingProfile.model_validate(row) if row else None


async def get_branding_profile(
    session: AsyncSession, account_id: uuid.UUID
) -> BrandingProfile | None:
    """The account's personal organisation's profile."""
    return await get_branding_profile_for_org(session, await personal_org_id(session, account_id))


async def upsert_branding_profile(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    org_id: uuid.UUID | None = None,
    **fields: str | None,
) -> BrandingProfile:
    """One profile per organisation (default: `account_id`'s personal org);
    `account_id` records who saved it. `fields` are applied as a partial
    update — only keys actually passed are written; a field the caller never
    mentions keeps its existing value rather than being reset to `None` (the
    caller, `apps/api`'s `PUT /v1/me/branding-profile`, passes
    `body.model_dump(exclude_unset=True)` so an omitted request field never
    reaches here at all, while an explicit `null` in the request does still
    clear it)."""
    org_id = org_id or await personal_org_id(session, account_id)
    result = await session.execute(
        select(BrandingProfileRow).where(BrandingProfileRow.org_id == org_id)
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = BrandingProfileRow(account_id=account_id, org_id=org_id)
        session.add(row)
    else:
        row.account_id = account_id

    for key, value in fields.items():
        setattr(row, key, value)

    await session.flush()
    # `updated_at`'s server-side onupdate=func.now() isn't known to the
    # ORM object after an UPDATE (only INSERT gets it for free via
    # RETURNING) — refresh so model_validate() never lazy-loads it
    # outside an async context.
    await session.refresh(row)
    return BrandingProfile.model_validate(row)
