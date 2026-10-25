"""`POST`/`GET /v1/targets/{target_id}/monitors`, `POST
/v1/monitors/{monitor_id}/disable`, `GET /v1/targets/{target_id}/scores`,
`GET /v1/targets/{target_id}/alerts` (Phase 8). Scheduling itself
(`check_due_monitors_job`) and diffing (`detect_regression_job`) run in
`apps/scanner`'s worker, never here — this router only ever creates or
reads the `Monitor`/`Alert` rows those jobs act on.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from vigilo_api.access import (
    count_monitors_for_org,
    org_id_for_target,
    plan_id_for_target,
    require_target_role,
)
from vigilo_api.audit_log import record
from vigilo_api.deps import AccountDep, SessionDep
from vigilo_api.schemas import AlertResponse, MonitorCreate, MonitorResponse, ScoreHistoryEntry
from vigilo_billing import Meter, QuotaExceeded, consume, entitlements
from vigilo_monitoring import (
    create_monitor,
    get_monitor,
    get_monitor_by_target,
    list_alerts_for_target,
)
from vigilo_monitoring import disable_monitor as disable_monitor_row
from vigilo_orchestrator.service import list_scans_for_target
from vigilo_project.repository import get_project

router = APIRouter(tags=["monitors"])


def _to_response(monitor) -> MonitorResponse:
    return MonitorResponse(
        monitor_id=monitor.id,
        target_id=monitor.target_id,
        cadence_hours=monitor.cadence_hours,
        enabled=monitor.enabled,
        next_run_at=monitor.next_run_at,
        quiet_start_utc=monitor.quiet_start_utc,
        quiet_end_utc=monitor.quiet_end_utc,
    )


def _validate_cadence(cadence_hours: int, monitoring_frequency: str | None) -> None:
    if monitoring_frequency is None:
        raise QuotaExceeded("monitoring is not included in the account's plan")
    if monitoring_frequency == "weekly" and cadence_hours != 168:
        raise HTTPException(
            status_code=422, detail="this plan only supports a fixed weekly (168h) cadence"
        )
    if monitoring_frequency == "daily+custom" and not (1 <= cadence_hours <= 168):
        raise HTTPException(status_code=422, detail="cadence_hours must be between 1 and 168")


@router.post("/v1/targets/{target_id}/monitors", status_code=201)
async def create_target_monitor(
    target_id: uuid.UUID,
    body: MonitorCreate,
    account: AccountDep,
    session: SessionDep,
) -> MonitorResponse:
    target = await require_target_role(session, account, target_id, "member")
    plan = entitlements(await plan_id_for_target(session, target.id))
    _validate_cadence(body.cadence_hours, plan.monitoring_frequency)

    # A genuinely new monitor consumes the MONITORS quota; re-enabling or
    # re-configuring an existing one (create_monitor is idempotent by
    # target) does not — matches POST /v1/targets' own
    # only-count-if-new precedent.
    if await get_monitor_by_target(session, target.id) is None:
        current_count = await count_monitors_for_org(
            session, (await get_project(session, target.project_id)).org_id
        )
        decision = consume(current_count, 1, Meter.MONITORS, plan)
        if not decision.allowed:
            raise QuotaExceeded(
                "monitors limit reached for plan", limit=decision.limit, current=decision.current
            )

    monitor = await create_monitor(
        session,
        target_id=target.id,
        account_id=account.id,
        cadence_hours=body.cadence_hours,
        next_run_at=datetime.now(UTC),
        quiet_start_utc=body.quiet_start_utc,
        quiet_end_utc=body.quiet_end_utc,
    )
    await record(
        session,
        account,
        (await get_project(session, target.project_id)).org_id,
        "monitor_enabled",
        target.origin,
        cadence_hours=body.cadence_hours,
    )
    return _to_response(monitor)


@router.get("/v1/targets/{target_id}/monitors")
async def get_target_monitor(
    target_id: uuid.UUID, account: AccountDep, session: SessionDep
) -> MonitorResponse:
    target = await require_target_role(session, account, target_id, "viewer")
    monitor = await get_monitor_by_target(session, target.id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="no monitor for this target")
    return _to_response(monitor)


@router.post("/v1/monitors/{monitor_id}/disable")
async def disable_target_monitor(
    monitor_id: uuid.UUID, account: AccountDep, session: SessionDep
) -> MonitorResponse:
    # Ownership must be checked *before* mutating — a plain 404 on mismatch
    # (not 403) so ownership can't be probed by status code, matching
    # targets.py's precedent.
    existing = await get_monitor(session, monitor_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    target = await require_target_role(session, account, existing.target_id, "member")

    monitor = await disable_monitor_row(session, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    await record(
        session,
        account,
        await org_id_for_target(session, target.id),
        "monitor_disabled",
        target.origin,
    )
    return _to_response(monitor)


@router.get("/v1/targets/{target_id}/scores")
async def get_target_score_history(
    target_id: uuid.UUID, account: AccountDep, session: SessionDep
) -> list[ScoreHistoryEntry]:
    target = await require_target_role(session, account, target_id, "viewer")
    scans = await list_scans_for_target(session, target.id)
    return [
        ScoreHistoryEntry(
            scan_id=scan.id,
            score=scan.score,
            grade=scan.grade,
            registry_version=scan.registry_version,
            created_at=scan.created_at,
        )
        for scan in scans
    ]


@router.get("/v1/targets/{target_id}/alerts")
async def get_target_alerts(
    target_id: uuid.UUID, account: AccountDep, session: SessionDep
) -> list[AlertResponse]:
    target = await require_target_role(session, account, target_id, "viewer")
    alerts = await list_alerts_for_target(session, target.id)
    return [
        AlertResponse(
            alert_id=alert.id,
            type=alert.type,
            severity=alert.severity,
            fingerprint=alert.fingerprint,
            sent_at=alert.sent_at,
            created_at=alert.created_at,
        )
        for alert in alerts
    ]
