"""FastAPI dependencies: a per-request DB session, the Clerk-authenticated
account, and the ARQ enqueue pool.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from vigilo_api.access import ActiveOrg, resolve_active_org
from vigilo_api.auth import ClerkAuthError, verify_clerk_jwt
from vigilo_api.queue import get_arq_pool
from vigilo_identity.models import Account, Membership
from vigilo_identity.org_repository import OrgError, get_membership, plan_id_for_org, role_at_least
from vigilo_identity.repository import (
    get_account_by_clerk_id,
    get_or_create_account,
    link_clerk_org,
)
from vigilo_persistence import session_scope


async def get_session() -> AsyncIterator[AsyncSession]:
    """One session per request, committed on a clean response and rolled
    back on any exception — including an `HTTPException` raised mid-handler.
    Endpoints that must persist a decision before an error response (e.g. a
    denied scan's audit event) commit explicitly before raising."""
    async with session_scope() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return header.removeprefix("Bearer ")


async def require_account(request: Request, session: SessionDep) -> Account:
    token = _bearer_token(request)
    try:
        claims = verify_clerk_jwt(token)
    except ClerkAuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc

    request.state.clerk_claims = claims
    account = await get_account_by_clerk_id(session, claims.user_id)
    if account is not None:
        return account

    if not claims.email:
        raise HTTPException(status_code=401, detail="session token has no email claim")
    return await get_or_create_account(session, email=claims.email, clerk_user_id=claims.user_id)


AccountDep = Annotated[Account, Depends(require_account)]


async def optional_account(request: Request, session: SessionDep) -> Account | None:
    """Missing `Authorization` header → anonymous view (`None`). A header
    that IS present but invalid/expired still raises `401` — never silently
    swallowed into an anonymous view, which would hide a real auth error
    from the caller."""
    if "Authorization" not in request.headers:
        return None
    return await require_account(request, session)


OptionalAccountDep = Annotated[Account | None, Depends(optional_account)]


async def get_queue() -> ArqRedis:
    return await get_arq_pool()


QueueDep = Annotated[ArqRedis, Depends(get_queue)]


# --- Organization scope -------------------------------------------------


def require_org_role(minimum: str):
    """Dependency factory: the caller must belong to `{org_id}` with at least
    `minimum` role. A non-member gets 404, never 403 — an org's existence is
    not disclosed to outsiders. A member below `minimum` gets 403."""

    async def dep(org_id: uuid.UUID, account: AccountDep, session: SessionDep) -> Membership:
        membership = await get_membership(session, org_id, account.id)
        if membership is None:
            raise HTTPException(status_code=404, detail="organization not found")
        if not role_at_least(membership.role, minimum):
            raise HTTPException(status_code=403, detail=f"requires {minimum} role")
        return membership

    return dep


async def claimed_org(
    request: Request, account: Account, session: AsyncSession
) -> ActiveOrg | None:
    """The Vigilo organisation for the Clerk organisation the token names (ADR-0014),
    linked or created on first use; None when the token names none."""
    claims = getattr(request.state, "clerk_claims", None)
    if claims is None or not claims.org_id:
        return None
    org, role = await link_clerk_org(
        session, account, claims.org_id, claims.org_role, claims.org_name
    )
    return ActiveOrg(org.id, role, await plan_id_for_org(session, org.id))


async def active_org(
    request: Request,
    account: AccountDep,
    session: SessionDep,
    x_org_id: Annotated[str | None, Header()] = None,
) -> ActiveOrg:
    """The organisation list/create routes act in: `X-Org-Id` if sent, else the Clerk
    organisation the token names (ADR-0014; linked or created on first use), else the
    caller's personal organisation. See `vigilo_api.access`."""
    if not x_org_id:
        try:
            claimed = await claimed_org(request, account, session)
        except OrgError as exc:
            raise HTTPException(status_code=409, detail=exc.message) from exc
        if claimed is not None:
            return claimed
    return await resolve_active_org(session, account, x_org_id)


ActiveOrgDep = Annotated[ActiveOrg, Depends(active_org)]
