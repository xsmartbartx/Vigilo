"""Members removed in Clerk lose their access in a linked organisation (ADR-0014)."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from vigilo_api.clerk_member_sync import sync_clerk_members
from vigilo_core.config import config
from vigilo_identity.orm import MembershipRow
from vigilo_identity.repository import get_or_create_account, link_clerk_org
from vigilo_integrations.clerk import list_clerk_org_member_ids
from vigilo_integrations.errors import IdentityProviderError
from vigilo_persistence import session_scope

CLERK_ORG = "org_2abcdefghijk"


async def _team():
    """An owner (Clerk admin), a member and a second admin in one linked organisation."""
    async with session_scope() as session:
        owner = await get_or_create_account(session, email="o@example.com", clerk_user_id="u_owner")
        member = await get_or_create_account(session, email="m@example.com", clerk_user_id="u_mem")
        admin = await get_or_create_account(session, email="a@example.com", clerk_user_id="u_adm")
        org, _ = await link_clerk_org(session, owner, CLERK_ORG, "org:admin", "Acme")
        await link_clerk_org(session, member, CLERK_ORG, "org:member")
        await link_clerk_org(session, admin, CLERK_ORG, "org:admin")
    return org.id


async def _roles(org_id) -> dict[str, str]:
    async with session_scope() as session:
        rows = (
            await session.execute(select(MembershipRow).where(MembershipRow.org_id == org_id))
        ).scalars()
        return {str(r.account_id): r.role for r in rows}


def _fetch(ids):
    async def fetch(_org: str):
        return ids

    return fetch


async def test_members_missing_from_clerk_are_removed_but_owners_never(client):
    org_id = await _team()
    assert len(await _roles(org_id)) == 3

    # Clerk now lists only the member: the owner and the second admin are gone from it.
    result = await sync_clerk_members(_fetch({"u_mem"}))

    roles = await _roles(org_id)
    assert result.removed == 1  # the second admin
    assert sorted(roles.values()) == ["member", "owner"]  # the owner stays despite not listed


async def test_nothing_is_removed_when_clerk_cannot_be_read_or_returns_nothing(client):
    org_id = await _team()

    for answer in (None, set()):
        result = await sync_clerk_members(_fetch(answer))
        assert result.removed == 0
        assert result.skipped == 1

    async def broken(_org: str):
        raise IdentityProviderError("down")

    assert (await sync_clerk_members(broken)).removed == 0
    assert len(await _roles(org_id)) == 3


async def test_a_full_member_list_changes_nothing(client):
    org_id = await _team()
    result = await sync_clerk_members(_fetch({"u_owner", "u_mem", "u_adm"}))
    assert result.removed == 0
    assert len(await _roles(org_id)) == 3


async def test_organisations_not_linked_to_clerk_are_left_alone(client):
    async with session_scope() as session:
        a = await get_or_create_account(session, email="p@example.com", clerk_user_id="u_p")
        from vigilo_identity.org_repository import ensure_personal_org

        await ensure_personal_org(session, a)
    assert (await sync_clerk_members(_fetch({"someone-else"}))).organisations == 0


class TestListing:
    @pytest.fixture(autouse=True)
    def _key(self, monkeypatch):
        monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_x")
        config.cache_clear()
        yield
        config.cache_clear()

    @staticmethod
    def _member(uid):
        return {"public_user_data": {"user_id": uid}}

    async def test_reads_every_page(self):
        pages = {
            "0": {"data": [self._member(f"u{i}") for i in range(100)], "total_count": 101},
            "100": {"data": [self._member("u100")], "total_count": 101},
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer sk_test_x"
            return httpx.Response(200, json=pages[request.url.params["offset"]])

        ids = await list_clerk_org_member_ids(CLERK_ORG, httpx.MockTransport(handler))
        assert ids is not None
        assert len(ids) == 101

    async def test_a_missing_organisation_is_none_and_other_errors_raise(self):
        gone = httpx.MockTransport(lambda r: httpx.Response(404))
        assert await list_clerk_org_member_ids(CLERK_ORG, gone) is None
        broken = httpx.MockTransport(lambda r: httpx.Response(500))
        with pytest.raises(IdentityProviderError):
            await list_clerk_org_member_ids(CLERK_ORG, broken)

    async def test_a_listing_with_a_membership_lacking_a_user_is_rejected(self):
        body = {
            "data": [self._member("u1"), {"public_user_data": None}],
            "total_count": 2,
        }
        transport = httpx.MockTransport(lambda r: httpx.Response(200, json=body))
        with pytest.raises(IdentityProviderError):
            await list_clerk_org_member_ids(CLERK_ORG, transport)

    async def test_a_listing_shorter_than_its_total_is_rejected(self):
        body = {"data": [self._member("u1")], "total_count": 3}
        transport = httpx.MockTransport(lambda r: httpx.Response(200, json=body))
        with pytest.raises(IdentityProviderError):
            await list_clerk_org_member_ids(CLERK_ORG, transport)
