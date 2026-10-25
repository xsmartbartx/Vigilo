"""ADR-0014 phase 2: a Clerk token that names an organisation links (or creates) the
matching Vigilo organisation, and a plan Core sent earlier applies when it does."""

from __future__ import annotations

import json
import time

from sqlalchemy import select

import vigilo_api.deps as deps
from vigilo_api.auth import ClerkClaims, verify_clerk_jwt
from vigilo_api.core_sync import sign
from vigilo_core.config import config
from vigilo_identity.orm import MembershipRow, OrganizationRow
from vigilo_persistence import session_scope

CLERK_ORG = "org_2abcdefghijk"


def _token_as(monkeypatch, **claims):
    base = {"user_id": "user_a", "email": "a@example.com"}
    monkeypatch.setattr(deps, "verify_clerk_jwt", lambda _t: ClerkClaims(**{**base, **claims}))
    return {"Authorization": "Bearer t"}


async def _orgs(client, headers):
    resp = await client.get("/v1/orgs", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestClaims:
    def test_template_claims_and_session_v2_object_both_read(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        def tok(**c):
            return jwt.encode(
                {"sub": "u", "exp": int(time.time()) + 60, **c}, key, algorithm="RS256"
            )

        get = lambda _t: key.public_key()  # noqa: E731
        a = verify_clerk_jwt(
            tok(org_id=CLERK_ORG, org_role="org:admin", org_name="Acme"), get_signing_key=get
        )
        assert (a.org_id, a.org_role, a.org_name) == (CLERK_ORG, "org:admin", "Acme")
        b = verify_clerk_jwt(tok(o={"id": CLERK_ORG, "rol": "member"}), get_signing_key=get)
        assert (b.org_id, b.org_role) == (CLERK_ORG, "org:member")
        c = verify_clerk_jwt(tok(), get_signing_key=get)
        assert c.org_id is None


async def test_an_admins_first_visit_creates_and_links_the_organisation(client, monkeypatch):
    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin", org_name="Acme Inc")

    orgs = await _orgs(client, headers)

    team = [o for o in orgs if not o["is_personal"]]
    assert len(team) == 1
    assert team[0]["name"] == "Acme Inc"
    assert team[0]["role"] == "owner"
    async with session_scope() as session:
        row = (await session.execute(select(OrganizationRow))).scalars().all()
    assert [r.clerk_org_id for r in row if not r.is_personal] == [CLERK_ORG]


async def test_repeat_visits_do_not_create_a_second_organisation(client, monkeypatch):
    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin")
    await _orgs(client, headers)
    await _orgs(client, headers)
    assert len([o for o in await _orgs(client, headers) if not o["is_personal"]]) == 1


async def test_a_member_joins_with_the_member_role(client, monkeypatch):
    await _orgs(client, _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin"))

    headers = _token_as(
        monkeypatch,
        user_id="user_b",
        email="b@example.com",
        org_id=CLERK_ORG,
        org_role="org:member",
    )
    team = [o for o in await _orgs(client, headers) if not o["is_personal"]]

    assert [o["role"] for o in team] == ["member"]
    async with session_scope() as session:
        n = (await session.execute(select(MembershipRow))).scalars().all()
    # two personal workspaces and the team's owner; user_b is only a member
    assert len([m for m in n if m.role == "owner"]) == 3


async def test_a_member_cannot_set_up_an_organisation_nobody_opened(client, monkeypatch):
    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:member")

    assert [o for o in await _orgs(client, headers) if not o["is_personal"]] == []
    resp = await client.get("/v1/me/api-keys", headers=headers)
    assert resp.status_code == 409


async def test_an_owner_is_never_demoted_by_a_token(client, monkeypatch):
    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin")
    await _orgs(client, headers)
    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:member")
    team = [o for o in await _orgs(client, headers) if not o["is_personal"]]
    assert team[0]["role"] == "owner"


async def test_an_explicit_x_org_id_wins_over_the_token(client, monkeypatch):
    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin")
    personal = next(o for o in await _orgs(client, headers) if o["is_personal"])
    resp = await client.get("/v1/me/api-keys", headers={**headers, "X-Org-Id": personal["org_id"]})
    assert resp.status_code == 200


async def test_a_plan_core_sent_before_anyone_opened_vigilo_applies_on_the_first_visit(
    client, monkeypatch
):
    monkeypatch.setenv("NEXORA_SYNC_SECRET", "s3cret")
    config.cache_clear()
    raw = json.dumps({"clerk_org_id": CLERK_ORG, "plan_id": "pro"}).encode()
    ts = int(time.time())
    resp = await client.post(
        "/v1/internal/org-plan",
        content=raw,
        headers={
            "X-Nexora-Timestamp": str(ts),
            "X-Nexora-Signature": sign("s3cret", ts, raw),
            "Content-Type": "application/json",
        },
    )
    assert resp.json() == {"status": "ignored"}  # remembered, nothing linked yet

    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin")
    team = [o for o in await _orgs(client, headers) if not o["is_personal"]]

    assert team[0]["entitlements"]["plan_id"] == "pro"
    config.cache_clear()


async def test_only_the_organisation_the_token_names_is_flagged_as_claimed(client, monkeypatch):
    plain = _token_as(monkeypatch)
    assert [o["is_claimed"] for o in await _orgs(client, plain)] == [False]

    headers = _token_as(monkeypatch, org_id=CLERK_ORG, org_role="org:admin")
    orgs = await _orgs(client, headers)

    assert {o["is_personal"]: o["is_claimed"] for o in orgs} == {True: False, False: True}
