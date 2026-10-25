from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio

import vigilo_identity.orm  # noqa: F401
import vigilo_orchestrator.orm  # noqa: F401
import vigilo_project.orm  # noqa: F401
import vigilo_security.orm  # noqa: F401
from vigilo_api.main import app
from vigilo_persistence.testing import temporary_schema
from vigilo_security.rate_limit import get_redis_client


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """An `httpx.AsyncClient` over an ASGI transport, run directly on the
    calling test's event loop — deliberately not Starlette's `TestClient`,
    which drives the app from a separate portal thread/loop and would
    conflict with `vigilo_persistence.engine.get_engine()`'s cached,
    loop-bound asyncpg connection pool (the same "attached to a different
    loop" failure mode the session-scoped pytest-asyncio loop config
    elsewhere in this repo works around)."""
    # The anonymous-scan throttle keeps its counters in Redis for an hour; start every
    # test from empty counters so one test's submissions never count against the next.
    redis = get_redis_client()
    async for key in redis.scan_iter("scanrate:*"):
        await redis.delete(key)
    async with temporary_schema():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client
    app.dependency_overrides.clear()
