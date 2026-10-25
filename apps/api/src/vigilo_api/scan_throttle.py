"""Throttle for the anonymous free-scan route (`POST /v1/scans`).

That route needs no account, so nothing but the per-target 24-hour ceiling slowed a
caller who submitted many different URLs. This adds a fixed-window limit per client
address and per submitter email (the same Redis limiter the API keys use), so one
caller cannot use the service as a scan relay or fill the queue.

Defaults: 30 submissions per hour per address, 10 per hour per email. Override with
SCAN_RATE_PER_IP_PER_HOUR and SCAN_RATE_PER_EMAIL_PER_HOUR; `0` turns that limit off.
"""

from __future__ import annotations

import hashlib
import os

from fastapi import HTTPException, Request

from vigilo_security.rate_limit import check_rate, get_redis_client

_HOUR = 3600
_DEFAULT_PER_IP = 30
_DEFAULT_PER_EMAIL = 10


def _limit(name: str, default: int) -> int | None:
    raw = os.environ.get(name, "").strip()
    value = default if not raw else int(raw)
    return None if value == 0 else value


def client_address(request: Request) -> str:
    """The address our reverse proxy saw. The proxy appends the real client to
    X-Forwarded-For, so the LAST entry is the one we can trust; earlier entries are
    whatever the caller sent. Without a proxy, fall back to the socket peer."""
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if parts:
        return parts[-1]
    return request.client.host if request.client else "unknown"


async def enforce_scan_limits(request: Request, email: str) -> None:
    redis = get_redis_client()
    email_key = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]
    checks = (
        (
            f"scanrate:ip:{client_address(request)}",
            _limit("SCAN_RATE_PER_IP_PER_HOUR", _DEFAULT_PER_IP),
        ),
        (f"scanrate:email:{email_key}", _limit("SCAN_RATE_PER_EMAIL_PER_HOUR", _DEFAULT_PER_EMAIL)),
    )
    for key, limit in checks:
        decision = await check_rate(redis, key, limit, _HOUR)
        if not decision.allowed:
            raise HTTPException(
                status_code=429,
                detail="too many scans submitted; try again later",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
