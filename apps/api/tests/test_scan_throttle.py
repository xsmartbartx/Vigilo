"""The anonymous free-scan route is throttled per client address and per email."""

import pytest


def _body(email: str) -> dict:
    return {"target_url": "https://example.com", "email": email}


def _from(address: str) -> dict:
    return {"X-Forwarded-For": address}


async def test_one_address_is_limited_but_another_is_not(client, monkeypatch):
    monkeypatch.setenv("SCAN_RATE_PER_IP_PER_HOUR", "2")
    monkeypatch.setenv("SCAN_RATE_PER_EMAIL_PER_HOUR", "0")
    for i in range(2):
        r = await client.post(
            "/v1/scans", json=_body(f"a{i}@example.com"), headers=_from("203.0.113.5")
        )
        assert r.status_code == 202

    blocked = await client.post(
        "/v1/scans", json=_body("a9@example.com"), headers=_from("203.0.113.5")
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1

    other = await client.post(
        "/v1/scans", json=_body("b0@example.com"), headers=_from("203.0.113.6")
    )
    assert other.status_code == 202


async def test_one_email_is_limited_across_addresses(client, monkeypatch):
    monkeypatch.setenv("SCAN_RATE_PER_IP_PER_HOUR", "0")
    monkeypatch.setenv("SCAN_RATE_PER_EMAIL_PER_HOUR", "1")
    first = await client.post(
        "/v1/scans", json=_body("Same@Example.com"), headers=_from("198.51.100.1")
    )
    assert first.status_code == 202
    second = await client.post(
        "/v1/scans", json=_body("same@example.com "), headers=_from("198.51.100.2")
    )
    assert second.status_code == 429  # case and surrounding spaces do not make a new person

    different = await client.post(
        "/v1/scans", json=_body("else@example.com"), headers=_from("198.51.100.2")
    )
    assert different.status_code == 202


async def test_a_caller_cannot_dodge_the_limit_by_forging_forwarded_for(client, monkeypatch):
    monkeypatch.setenv("SCAN_RATE_PER_IP_PER_HOUR", "1")
    monkeypatch.setenv("SCAN_RATE_PER_EMAIL_PER_HOUR", "0")
    # The proxy appends the real address last; what the caller put before it is ignored.
    ok = await client.post(
        "/v1/scans", json=_body("f0@example.com"), headers=_from("1.1.1.1, 192.0.2.77")
    )
    assert ok.status_code == 202
    again = await client.post(
        "/v1/scans", json=_body("f1@example.com"), headers=_from("2.2.2.2, 192.0.2.77")
    )
    assert again.status_code == 429


@pytest.mark.parametrize("name", ["SCAN_RATE_PER_IP_PER_HOUR", "SCAN_RATE_PER_EMAIL_PER_HOUR"])
async def test_zero_turns_a_limit_off(client, monkeypatch, name):
    monkeypatch.setenv("SCAN_RATE_PER_IP_PER_HOUR", "0")
    monkeypatch.setenv("SCAN_RATE_PER_EMAIL_PER_HOUR", "0")
    monkeypatch.setenv(name, "0")
    for i in range(3):
        r = await client.post(
            "/v1/scans", json=_body(f"z{i}@example.com"), headers=_from("192.0.2.1")
        )
        assert r.status_code == 202
