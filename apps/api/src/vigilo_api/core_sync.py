"""Verification of the plan updates NEXORA Core sends for organisation accounts.

Core signs `"<unix-seconds>.<raw body>"` with HMAC-SHA256 and a secret both sides
hold (`NEXORA_SYNC_SECRET`). The timestamp bounds replay, the HMAC covers the exact
bytes, and the comparison is constant-time. Every rejection looks the same to the
caller, so a probe cannot learn which check failed.
"""

from __future__ import annotations

import hashlib
import hmac
import time

REPLAY_WINDOW_SECONDS = 300


def sign(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def verify(
    secret: str,
    timestamp_header: str | None,
    signature_header: str | None,
    body: bytes,
    now: float | None = None,
) -> bool:
    if not timestamp_header or not signature_header:
        return False
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - timestamp) > REPLAY_WINDOW_SECONDS:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), signature_header)
