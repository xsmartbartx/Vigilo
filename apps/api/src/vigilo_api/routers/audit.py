"""`GET /v1/orgs/{org_id}/audit` — the organisation's activity trail, for owners
and admins. Read-only: the table is append-only at the database level."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from vigilo_api.audit_log import decode_cursor, list_audit_entries
from vigilo_api.deps import SessionDep, require_org_role
from vigilo_identity.models import Membership

router = APIRouter(prefix="/v1", tags=["audit"])

Admin = Annotated[Membership, Depends(require_org_role("admin"))]


class AuditEntryResponse(BaseModel):
    event_id: uuid.UUID
    occurred_at: datetime
    action: str
    subject: str
    actor_kind: str
    actor_label: str
    details: dict


class AuditPageResponse(BaseModel):
    events: list[AuditEntryResponse]
    next_cursor: str | None
    actions: list[str]


@router.get("/orgs/{org_id}/audit")
async def get_audit_log(
    org_id: uuid.UUID,
    admin: Admin,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    action: Annotated[str | None, Query(pattern=r"^[a-z_]{1,64}$")] = None,
) -> AuditPageResponse:
    before = None
    if cursor:
        try:
            before = decode_cursor(cursor)
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail="invalid cursor") from exc
    entries, next_cursor, actions = await list_audit_entries(
        session, org_id, limit=limit, before=before, action=action
    )
    return AuditPageResponse(
        events=[
            AuditEntryResponse(
                event_id=e.id,
                occurred_at=e.occurred_at,
                action=e.action,
                subject=e.subject,
                actor_kind=e.actor_kind,
                actor_label=e.actor_label,
                details=e.details,
            )
            for e in entries
        ],
        next_cursor=next_cursor,
        actions=actions,
    )
