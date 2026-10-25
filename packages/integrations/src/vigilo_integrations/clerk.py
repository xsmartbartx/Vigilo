"""Clerk's Backend API, for what the product needs it for: removing a user's sign-in
identity when they delete their account (without it the person could sign in again and be
given a fresh, empty account), and listing who is in a Clerk organisation so people removed
there lose access here. No SDK; `transport` is the same `httpx.MockTransport` seam the
other adapters use.
"""

from __future__ import annotations

import httpx

from vigilo_core.config import config
from vigilo_integrations.errors import IdentityProviderError

_USERS_URL = "https://api.clerk.com/v1/users"
_REQUEST_TIMEOUT = 10.0


async def delete_clerk_user(
    clerk_user_id: str, transport: httpx.AsyncBaseTransport | None = None
) -> None:
    """Idempotent: a user Clerk no longer has (404) counts as deleted."""
    cfg = config()
    if not cfg.clerk_secret_key:
        raise IdentityProviderError("Clerk is not configured (missing secret key)")
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT, transport=transport) as client:
            response = await client.delete(
                f"{_USERS_URL}/{clerk_user_id}",
                headers={"Authorization": f"Bearer {cfg.clerk_secret_key}"},
            )
    except httpx.HTTPError as exc:
        raise IdentityProviderError("Clerk request failed") from exc
    if response.status_code == 404:
        return
    if response.status_code >= 400:
        raise IdentityProviderError(
            "Clerk rejected the user deletion", status_code=response.status_code
        )


_ORGS_URL = "https://api.clerk.com/v1/organizations"
_PAGE = 100
_MAX_PAGES = 100  # 10,000 members: a runaway loop is worse than an incomplete list


async def list_clerk_org_member_ids(
    clerk_org_id: str, transport: httpx.AsyncBaseTransport | None = None
) -> set[str] | None:
    """The Clerk user ids in an organisation, or None when Clerk no longer has it (404).
    Raises `IdentityProviderError` on any other failure, including an unfinished listing,
    so a caller never mistakes a partial list for the whole membership."""
    cfg = config()
    if not cfg.clerk_secret_key:
        raise IdentityProviderError("Clerk is not configured (missing secret key)")
    ids: set[str] = set()
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT, transport=transport) as client:
            for page in range(_MAX_PAGES):
                response = await client.get(
                    f"{_ORGS_URL}/{clerk_org_id}/memberships",
                    params={"limit": _PAGE, "offset": page * _PAGE},
                    headers={"Authorization": f"Bearer {cfg.clerk_secret_key}"},
                )
                if response.status_code == 404:
                    return None
                if response.status_code >= 400:
                    raise IdentityProviderError(
                        "Clerk rejected the membership listing", status_code=response.status_code
                    )
                body = response.json()
                batch = body.get("data", [])
                for membership in batch:
                    # user data is nullable in Clerk's API; a membership without an id means
                    # the listing is incomplete, and acting on it would remove real members.
                    ids.add(membership["public_user_data"]["user_id"])
                total = body["total_count"]
                if len(batch) < _PAGE or len(ids) >= total:
                    if len(ids) != total:
                        raise IdentityProviderError("Clerk membership listing is incomplete")
                    return ids
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise IdentityProviderError("Clerk membership listing failed") from exc
    raise IdentityProviderError("Clerk membership listing did not finish")
