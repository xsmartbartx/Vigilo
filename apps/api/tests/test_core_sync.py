"""NEXORA Core -> Vigilo plan sync: signature checks and the endpoint end to end."""

from __future__ import annotations

import json
import time

import pytest
from sqlalchemy import update

from vigilo_api.core_sync import REPLAY_WINDOW_SECONDS, sign, verify
from vigilo_api.deps import require_account
from vigilo_api.main import app
from vigilo_core.config import config
from vigilo_identity.org_repository import plan_id_for_org
from vigilo_identity.orm import OrganizationRow
from vigilo_identity.repository import get_or_create_account
from vigilo_persistence import session_scope

SECRET = "test-shared-secret"
CLERK_ORG = "org_2abcdefghijk"


def _signed(body: dict | bytes, ts: int | None = None, secret: str = SECRET) -> tuple[bytes, dict]:
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    ts = int(time.time()) if ts is None else ts
    return raw, {
        "X-Nexora-Timestamp": str(ts),
        "X-Nexora-Signature": sign(secret, ts, raw),
        "Content-Type": "application/json",
    }


class TestSignature:
    def test_accepts_a_fresh_correct_signature(self):
        body = b'{"x":1}'
        assert verify(SECRET, "1000", sign(SECRET, 1000, body), body, now=1000)

    def test_rejects_wrong_secret_tampered_body_and_missing_headers(self):
        body = b'{"x":1}'
        good = sign(SECRET, 1000, body)
        assert not verify("other", "1000", good, body, now=1000)
        assert not verify(SECRET, "1000", good, b'{"x":2}', now=1000)
        assert not verify(SECRET, None, good, body, now=1000)
        assert not verify(SECRET, "1000", None, body, now=1000)
        assert not verify(SECRET, "not-a-number", good, body, now=1000)

    def test_rejects_stale_and_future_timestamps(self):
        body = b"{}"
        sig = sign(SECRET, 1000, body)
        assert verify(SECRET, "1000", sig, body, now=1000 + REPLAY_WINDOW_SECONDS)
        assert not verify(SECRET, "1000", sig, body, now=1000 + REPLAY_WINDOW_SECONDS + 1)
        assert not verify(SECRET, "1000", sig, body, now=1000 - REPLAY_WINDOW_SECONDS - 1)


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setenv("NEXORA_SYNC_SECRET", SECRET)
    config.cache_clear()
    yield
    config.cache_clear()


@pytest.fixture(autouse=True)
def _no_overrides():
    yield
    app.dependency_overrides.pop(require_account, None)


async def _linked_org(client, clerk_org_id: str = CLERK_ORG) -> str:
    """A team organisation created in Vigilo and linked to a Clerk organisation."""
    async with session_scope() as session:
        owner = await get_or_create_account(session, email="owner@example.com", clerk_user_id="u1")
    app.dependency_overrides[require_account] = lambda: owner
    resp = await client.post("/v1/orgs", json={"name": "Acme", "slug": "acme"})
    assert resp.status_code == 201, resp.text
    org_id = resp.json()["org_id"]
    async with session_scope() as session:
        await session.execute(
            update(OrganizationRow)
            .where(OrganizationRow.slug == "acme")
            .values(clerk_org_id=clerk_org_id)
        )
    return org_id


async def _plan(org_id: str) -> str | None:
    import uuid

    async with session_scope() as session:
        return await plan_id_for_org(session, uuid.UUID(org_id))


async def test_the_endpoint_does_not_exist_until_a_secret_is_configured(client, monkeypatch):
    monkeypatch.delenv("NEXORA_SYNC_SECRET", raising=False)
    config.cache_clear()
    raw, headers = _signed({"clerk_org_id": CLERK_ORG, "plan_id": "pro"})
    assert (
        await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    ).status_code == 404


async def test_an_unsigned_or_badly_signed_call_is_a_401(client, secret):
    unsigned = await client.post(
        "/v1/internal/org-plan", json={}
    )  # what Core's own smoke test sends
    assert unsigned.status_code == 401
    raw, headers = _signed({"clerk_org_id": CLERK_ORG, "plan_id": "pro"}, secret="wrong")
    assert (
        await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    ).status_code == 401
    raw, headers = _signed(
        {"clerk_org_id": CLERK_ORG, "plan_id": "pro"}, ts=int(time.time()) - 3600
    )
    assert (
        await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    ).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"clerk_org_id": "not-an-org", "plan_id": "pro"},
        {"clerk_org_id": CLERK_ORG, "plan_id": "enterprise"},
        {"clerk_org_id": CLERK_ORG},
        {"plan_id": "pro"},
    ],
)
async def test_a_signed_but_malformed_payload_is_a_400(client, secret, payload):
    raw, headers = _signed(payload)
    assert (
        await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    ).status_code == 400


async def test_a_plan_for_an_unlinked_organisation_is_acknowledged_and_ignored(client, secret):
    raw, headers = _signed({"clerk_org_id": "org_neverseen12345", "plan_id": "pro"})
    resp = await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ignored"}


async def test_pro_then_free_changes_a_linked_organisations_plan(client, secret):
    org_id = await _linked_org(client)
    assert await _plan(org_id) is None  # free to begin with

    raw, headers = _signed({"clerk_org_id": CLERK_ORG, "plan_id": "pro"})
    resp = await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    assert resp.json() == {"status": "applied"}
    assert await _plan(org_id) == "pro"

    raw, headers = _signed({"clerk_org_id": CLERK_ORG, "plan_id": "free"})
    assert (
        await client.post("/v1/internal/org-plan", content=raw, headers=headers)
    ).status_code == 200
    assert await _plan(org_id) is None


async def test_the_same_update_twice_is_harmless(client, secret):
    org_id = await _linked_org(client)
    for _ in range(2):
        raw, headers = _signed({"clerk_org_id": CLERK_ORG, "plan_id": "pro"})
        assert (
            await client.post("/v1/internal/org-plan", content=raw, headers=headers)
        ).status_code == 200
    assert await _plan(org_id) == "pro"


async def test_a_core_billed_organisation_is_sent_to_the_console_not_the_stripe_portal(
    client, secret
):
    org_id = await _linked_org(client)
    raw, headers = _signed({"clerk_org_id": CLERK_ORG, "plan_id": "pro"})
    await client.post("/v1/internal/org-plan", content=raw, headers=headers)

    resp = await client.post("/v1/billing/portal", headers={"X-Org-Id": org_id})
    assert resp.status_code == 409
    assert "NEXORA Console" in resp.json()["detail"]
