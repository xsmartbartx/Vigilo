"""Clerk session-JWT verification (ADR-0003 Phase 3 addendum: Clerk chosen
over Supabase Auth). Stateless, JWKS-based — no Clerk SDK dependency.

`get_signing_key` is the same dependency-injection seam used throughout the
codebase (`egress_guard.Resolver`, `ownership.TxtResolver`): the default
fetches Clerk's real JWKS over the network; tests inject a fake key so
verification logic (signature, expiry, claim extraction) is tested with a
locally-generated keypair, never a live Clerk instance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from vigilo_core.config import config
from vigilo_core.errors import ErrorCode, StructuredError

GetSigningKey = Callable[[str], Any]


@dataclass(frozen=True)
class ClerkClaims:
    user_id: str
    email: str | None
    # The active Clerk organisation, when the token names one: the template shortcodes
    # (`org_id`, `org_role`, `org_name`) or Clerk's session-token v2 object `o`.
    org_id: str | None = None
    org_role: str | None = None
    org_name: str | None = None


class ClerkAuthError(StructuredError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, message, **context)


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    cfg = config()
    if not cfg.clerk_jwks_url:
        raise StructuredError(ErrorCode.CONFIGURATION_ERROR, "CLERK_JWKS_URL is not set")
    return PyJWKClient(cfg.clerk_jwks_url)


def _default_get_signing_key(token: str) -> Any:
    return _jwk_client().get_signing_key_from_jwt(token).key


def verify_clerk_jwt(token: str, get_signing_key: GetSigningKey | None = None) -> ClerkClaims:
    resolve = get_signing_key or _default_get_signing_key

    try:
        signing_key = resolve(token)
        payload = jwt.decode(
            token, signing_key, algorithms=["RS256"], options={"verify_aud": False}
        )
    except jwt.PyJWTError as exc:
        raise ClerkAuthError("invalid or expired session token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise ClerkAuthError("session token is missing a subject claim")

    v2 = payload.get("o") if isinstance(payload.get("o"), dict) else {}
    org_id = payload.get("org_id") or v2.get("id")
    org_role = payload.get("org_role") or (f"org:{v2['rol']}" if v2.get("rol") else None)
    return ClerkClaims(
        user_id=user_id,
        email=payload.get("email"),
        org_id=org_id if isinstance(org_id, str) and org_id else None,
        org_role=org_role if isinstance(org_role, str) else None,
        org_name=payload.get("org_name") if isinstance(payload.get("org_name"), str) else None,
    )
