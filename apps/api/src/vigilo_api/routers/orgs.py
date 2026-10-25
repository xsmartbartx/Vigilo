"""Organizations: tenancy, members, invites, product enablement, usage
(docs/architecture.md §5). Every `/v1/orgs/{org_id}/...` route is guarded by
`require_org_role`; a non-member sees 404.
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from vigilo_api.audit_log import record
from vigilo_api.deps import AccountDep, SessionDep, claimed_org, require_org_role
from vigilo_api.invite_email import EmailStatus, send_invite_email
from vigilo_api.schemas import EntitlementsResponse
from vigilo_billing import entitlements
from vigilo_identity.models import Membership
from vigilo_identity.org_repository import (
    AVAILABLE_PRODUCTS,
    PRODUCT_SLUGS,
    OrgError,
    accept_invite,
    create_invite,
    create_org,
    enable_product,
    ensure_personal_org,
    get_org,
    list_enablements,
    list_members,
    list_orgs_for_account,
    list_pending_invites,
    list_usage,
    period_start,
    plan_id_for_org,
    remove_member,
    revoke_invite,
    role_at_least,
    rotate_invite,
    set_member_role,
    transfer_ownership,
)

router = APIRouter(prefix="/v1", tags=["organizations"])

# Any member, including viewers, may read org state; writes need admin.
Member = Annotated[Membership, Depends(require_org_role("viewer"))]
Admin = Annotated[Membership, Depends(require_org_role("admin"))]

_STATUS = {
    "not_found": 404,
    "invalid_slug": 422,
    "invalid_role": 422,
    "invalid_amount": 422,
    "slug_taken": 409,
    "owner_immutable": 409,
    "already_member": 409,
    "expired": 410,
    "not_available": 409,
    "personal_org": 409,
    "invalid_target": 422,
    "not_owner": 403,
}


def _http(exc: OrgError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS.get(exc.code, 400), detail={"code": exc.code, "message": exc.message}
    )


class OrgResponse(BaseModel):
    org_id: uuid.UUID
    name: str
    slug: str
    is_personal: bool
    role: str
    # The organisation's entitlements: its owner's plan, whoever is asking.
    entitlements: EntitlementsResponse
    # True for the organisation the caller's Clerk token names (ADR-0014): the one to open
    # by default.
    is_claimed: bool = False


class OrgCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    slug: str = Field(min_length=2, max_length=48)


class MemberResponse(BaseModel):
    account_id: uuid.UUID
    email: str
    role: str


class RoleUpdate(BaseModel):
    role: str


class InviteCreate(BaseModel):
    email: str = Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: str = "member"


class InviteCreateResponse(BaseModel):
    invite_id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    token: str  # shown once
    # Whether we emailed it: the link above is always usable either way.
    email_status: EmailStatus = "not_configured"


class ProductResponse(BaseModel):
    slug: str
    enabled: bool
    # Whether this build can run it at all; if not, it cannot be enabled yet.
    available: bool = True


class UsageResponse(BaseModel):
    product_slug: str
    meter: str
    used: int
    limit: int | None
    period_start: str


async def _entitlements_for(session, org_id: uuid.UUID) -> EntitlementsResponse:
    return EntitlementsResponse.model_validate(entitlements(await plan_id_for_org(session, org_id)))


@router.get("/orgs")
async def list_my_orgs(
    request: Request, account: AccountDep, session: SessionDep
) -> list[OrgResponse]:
    await ensure_personal_org(session, account)
    # ADR-0014: link the token's organisation. Not set up yet by an admin: the list
    # simply does not include it.
    claimed = None
    with contextlib.suppress(OrgError):
        claimed = await claimed_org(request, account, session)
    rows = await list_orgs_for_account(session, account.id)
    return [
        OrgResponse(
            org_id=o.id,
            name=o.name,
            slug=o.slug,
            is_personal=o.is_personal,
            role=role,
            entitlements=await _entitlements_for(session, o.id),
            is_claimed=claimed is not None and claimed.org_id == o.id,
        )
        for o, role in rows
    ]


@router.post("/orgs", status_code=201)
async def create_my_org(body: OrgCreate, account: AccountDep, session: SessionDep) -> OrgResponse:
    try:
        org = await create_org(session, account, body.name, body.slug)
    except OrgError as exc:
        raise _http(exc) from exc
    await record(session, account, org.id, "org_created", org.slug, name=org.name)
    return OrgResponse(
        org_id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=False,
        role="owner",
        entitlements=await _entitlements_for(session, org.id),
    )


@router.get("/orgs/{org_id}/members")
async def get_members(org_id: uuid.UUID, _m: Member, session: SessionDep) -> list[MemberResponse]:
    return [MemberResponse(**m.model_dump()) for m in await list_members(session, org_id)]


async def _email_invite(session, org_id: uuid.UUID, account, invite, token: str) -> EmailStatus:
    """Commit first so the link is live before it is mailed, then send. A send
    failure never undoes the invite."""
    await session.commit()
    org = await get_org(session, org_id)
    return await send_invite_email(
        org_id=str(org_id),
        org_name=org.name if org else "",
        inviter_id=str(account.id),
        inviter_email=account.email,
        to=invite.email,
        role=invite.role,
        token=token,
        expires_at=invite.expires_at,
    )


@router.post("/orgs/{org_id}/invites", status_code=201)
async def invite_member(
    org_id: uuid.UUID, body: InviteCreate, admin: Admin, account: AccountDep, session: SessionDep
) -> InviteCreateResponse:
    try:
        invite, token = await create_invite(session, org_id, body.email, body.role, account.id)
    except OrgError as exc:
        raise _http(exc) from exc
    email_status = await _email_invite(session, org_id, account, invite, token)
    await record(
        session,
        account,
        org_id,
        "invite_created",
        invite.email,
        role=invite.role,
        email=email_status,
    )
    return InviteCreateResponse(
        invite_id=invite.id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        token=token,
        email_status=email_status,
    )


@router.post("/orgs/{org_id}/invites/{invite_id}/resend")
async def resend_invite(
    org_id: uuid.UUID, invite_id: uuid.UUID, admin: Admin, account: AccountDep, session: SessionDep
) -> InviteCreateResponse:
    """New link, new 7 days, emailed again. The previous link stops working."""
    try:
        invite, token = await rotate_invite(session, org_id, invite_id)
    except OrgError as exc:
        raise _http(exc) from exc
    email_status = await _email_invite(session, org_id, account, invite, token)
    await record(
        session,
        account,
        org_id,
        "invite_resent",
        invite.email,
        role=invite.role,
        email=email_status,
    )
    return InviteCreateResponse(
        invite_id=invite.id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        token=token,
        email_status=email_status,
    )


class PendingInviteResponse(BaseModel):
    invite_id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    created_at: datetime


@router.get("/orgs/{org_id}/invites")
async def get_pending_invites(
    org_id: uuid.UUID, admin: Admin, session: SessionDep
) -> list[PendingInviteResponse]:
    return [
        PendingInviteResponse(
            invite_id=i.id,
            email=i.email,
            role=i.role,
            expires_at=i.expires_at,
            created_at=i.created_at,
        )
        for i in await list_pending_invites(session, org_id)
    ]


@router.delete("/orgs/{org_id}/invites/{invite_id}", status_code=204)
async def delete_invite(
    org_id: uuid.UUID, invite_id: uuid.UUID, admin: Admin, account: AccountDep, session: SessionDep
) -> None:
    try:
        await revoke_invite(session, org_id, invite_id)
    except OrgError as exc:
        raise _http(exc) from exc
    await record(session, account, org_id, "invite_revoked", str(invite_id))


@router.post("/invites/{token}/accept")
async def accept_org_invite(token: str, account: AccountDep, session: SessionDep) -> OrgResponse:
    try:
        membership = await accept_invite(session, token, account)
    except OrgError as exc:
        raise _http(exc) from exc
    org = await get_org(session, membership.org_id)
    assert org is not None
    await record(session, account, org.id, "invite_accepted", account.email, role=membership.role)
    return OrgResponse(
        org_id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        role=membership.role,
        entitlements=await _entitlements_for(session, org.id),
    )


@router.patch("/orgs/{org_id}/members/{account_id}")
async def change_member_role(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    body: RoleUpdate,
    admin: Admin,
    account: AccountDep,
    session: SessionDep,
) -> MemberResponse:
    before = next(
        (m for m in await list_members(session, org_id) if m.account_id == account_id), None
    )
    try:
        await set_member_role(session, org_id, account_id, body.role)
    except OrgError as exc:
        raise _http(exc) from exc
    members = await list_members(session, org_id)
    changed = next(m for m in members if m.account_id == account_id)
    await record(
        session,
        account,
        org_id,
        "member_role_changed",
        changed.email,
        previous=before.role if before else None,
        role=changed.role,
    )
    return MemberResponse(**changed.model_dump())


@router.delete("/orgs/{org_id}/members/{account_id}", status_code=204)
async def delete_member(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    caller: Member,
    account: AccountDep,
    session: SessionDep,
) -> None:
    """An admin removes anyone but the owner; anyone may remove themselves
    (leave the organisation); the owner can do neither."""
    if account_id != caller.account_id and not role_at_least(caller.role, "admin"):
        raise HTTPException(status_code=403, detail="requires admin role")
    who = next((m for m in await list_members(session, org_id) if m.account_id == account_id), None)
    try:
        await remove_member(session, org_id, account_id)
    except OrgError as exc:
        raise _http(exc) from exc
    left = account_id == caller.account_id
    await record(
        session,
        account,
        org_id,
        "member_left" if left else "member_removed",
        who.email if who else str(account_id),
        role=who.role if who else None,
    )


class TransferOwnership(BaseModel):
    new_owner_account_id: uuid.UUID
    # Typed by the owner: the slug of the organisation being handed over.
    confirm_slug: str


Owner = Annotated[Membership, Depends(require_org_role("owner"))]


@router.post("/orgs/{org_id}/transfer-ownership")
async def transfer_org_ownership(
    org_id: uuid.UUID,
    body: TransferOwnership,
    owner: Owner,
    account: AccountDep,
    session: SessionDep,
) -> MemberResponse:
    """Owner only. The new owner must already be a member; the caller becomes an
    admin. One owner per organisation, always."""
    org = await get_org(session, org_id)
    if org is None or body.confirm_slug.strip() != org.slug:
        raise HTTPException(status_code=422, detail="type the organisation's address to confirm")
    members = {m.account_id: m for m in await list_members(session, org_id)}
    try:
        await transfer_ownership(session, org_id, account.id, body.new_owner_account_id)
    except OrgError as exc:
        raise _http(exc) from exc
    new_owner = members.get(body.new_owner_account_id)
    await record(
        session,
        account,
        org_id,
        "ownership_transferred",
        new_owner.email if new_owner else str(body.new_owner_account_id),
        previous_owner=account.email,
    )
    return MemberResponse(
        account_id=body.new_owner_account_id,
        email=new_owner.email if new_owner else "",
        role="owner",
    )


@router.get("/orgs/{org_id}/products")
async def get_products(org_id: uuid.UUID, _m: Member, session: SessionDep) -> list[ProductResponse]:
    enabled = {
        e.product_slug for e in await list_enablements(session, org_id) if e.status == "enabled"
    }
    return [
        ProductResponse(slug=s, enabled=s in enabled, available=s in AVAILABLE_PRODUCTS)
        for s in PRODUCT_SLUGS
    ]


@router.post("/orgs/{org_id}/products/{slug}/enable")
async def enable_org_product(
    org_id: uuid.UUID, slug: str, admin: Admin, account: AccountDep, session: SessionDep
) -> ProductResponse:
    try:
        e = await enable_product(session, org_id, slug)
    except OrgError as exc:
        raise _http(exc) from exc
    await record(session, account, org_id, "product_enabled", slug)
    return ProductResponse(slug=e.product_slug, enabled=e.status == "enabled")


@router.get("/orgs/{org_id}/usage")
async def get_usage(org_id: uuid.UUID, _m: Member, session: SessionDep) -> list[UsageResponse]:
    """This UTC month's counters (`usage_counters`), the same numbers the quotas
    enforce. Vigilo always appears, at 0 until the first scan."""
    # The organisation's own plan (its subscription), the same limit the quota enforces.
    vigilo_limit = entitlements(await plan_id_for_org(session, org_id)).scans_per_month_limit
    rows = {(c.product_slug, c.meter): c.count for c in await list_usage(session, org_id)}
    rows.setdefault(("vigilo", "scans"), 0)
    start = period_start().isoformat()
    return [
        UsageResponse(
            product_slug=slug,
            meter=meter,
            used=count,
            limit=vigilo_limit if (slug, meter) == ("vigilo", "scans") else None,
            period_start=start,
        )
        for (slug, meter), count in sorted(rows.items())
    ]
