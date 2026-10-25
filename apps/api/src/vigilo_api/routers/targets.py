"""`POST /v1/targets`, `GET /v1/targets/{id}`, and the ownership-verification
pair — exit criterion (b). The verification-check endpoint always enqueues
`verify_ownership_job`, never runs a verification method inline: "the
control plane never makes an outbound request to a target, ever"
(docs/architecture.md §3), a rule the ADR-0003 Phase 3 addendum extends to
every verification method, not only the ones that fetch the target.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from vigilo_api.access import plan_id_for_target, require_target_role
from vigilo_api.audit_log import record
from vigilo_api.deps import AccountDep, ActiveOrgDep, QueueDep, SessionDep
from vigilo_api.schemas import (
    EntitlementsResponse,
    TargetCreate,
    TargetResponse,
    VerificationCheckResponse,
    VerificationInitiate,
    VerificationInitiateResponse,
)
from vigilo_billing import Meter, QuotaExceeded, consume, entitlements
from vigilo_core.config import config
from vigilo_core.models import Target, VerificationMethod
from vigilo_core.validation import ValidationError, validate_target_url
from vigilo_identity.models import Account
from vigilo_project.repository import (
    count_targets_for_project,
    create_target,
    get_or_create_org_project,
    get_ownership_proof,
    get_target_by_origin,
    issue_ownership_proof,
    list_targets_for_project,
)

router = APIRouter(prefix="/v1/targets", tags=["targets"])


def _to_response(target: Target) -> TargetResponse:
    return TargetResponse(
        target_id=target.id,
        origin=target.origin,
        verification_status=target.verification_status,
        verified_at=target.verified_at,
        verification_method=target.verification_method,
    )


async def _target_or_404(
    session: AsyncSession, account: Account, target_id: uuid.UUID, minimum: str = "viewer"
) -> Target:
    """Org-aware: any member with at least `minimum` role; non-members get 404."""
    return await require_target_role(session, account, target_id, minimum)


@router.post("", status_code=201)
async def create_target_endpoint(
    body: TargetCreate,
    account: AccountDep,
    org: ActiveOrgDep,
    session: SessionDep,
) -> TargetResponse:
    org.require("member")
    try:
        origin = validate_target_url(body.origin)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    project = await get_or_create_org_project(session, org.org_id, account.id)

    # Re-adding an already-tracked origin is idempotent-by-origin
    # (create_target) and must never count against quota — only a genuinely
    # new target is metered.
    if await get_target_by_origin(session, project.id, origin) is None:
        current_count = await count_targets_for_project(session, project.id)
        decision = consume(current_count, 1, Meter.TARGETS, entitlements(org.plan_id))
        if not decision.allowed:
            raise QuotaExceeded(
                "targets limit reached for plan", limit=decision.limit, current=decision.current
            )

    is_new = await get_target_by_origin(session, project.id, origin) is None
    target = await create_target(session, project.id, origin)
    if is_new:
        await record(session, account, org.org_id, "target_added", origin)
    return _to_response(target)


@router.get("")
async def list_targets_endpoint(
    account: AccountDep,
    org: ActiveOrgDep,
    session: SessionDep,
) -> list[TargetResponse]:
    project = await get_or_create_org_project(session, org.org_id, account.id)
    targets = await list_targets_for_project(session, project.id)
    return [_to_response(target) for target in targets]


@router.get("/{target_id}")
async def get_target_endpoint(
    target_id: uuid.UUID,
    account: AccountDep,
    session: SessionDep,
) -> TargetResponse:
    target = await _target_or_404(session, account, target_id)
    response = _to_response(target)
    response.org_entitlements = EntitlementsResponse.model_validate(
        entitlements(await plan_id_for_target(session, target.id))
    )
    return response


@router.post("/{target_id}/verification", status_code=201)
async def initiate_verification(
    target_id: uuid.UUID,
    body: VerificationInitiate,
    account: AccountDep,
    session: SessionDep,
) -> VerificationInitiateResponse:
    target = await _target_or_404(session, account, target_id, "member")
    proof = await issue_ownership_proof(session, target.id, body.method)

    namespaces = config().brand.namespaces
    dns_key = namespaces.get("dnsVerificationKey", "vigilo-site-verification")
    wellknown_path = namespaces.get("wellKnownPath", "/.well-known/vigilo-verification.txt")

    instructions = {
        VerificationMethod.DNS_TXT: f"Add a DNS TXT record: {dns_key}={proof.nonce}",
        VerificationMethod.WELLKNOWN_FILE: (
            f"Serve a file at {wellknown_path} whose content is exactly: {proof.nonce}"
        ),
        VerificationMethod.META_TAG: (
            f'Add <meta name="{dns_key}" content="{proof.nonce}"> to your homepage <head>.'
        ),
        VerificationMethod.EMAIL: "Email verification is not yet available.",
    }[body.method]

    return VerificationInitiateResponse(
        proof_id=proof.id, method=body.method, nonce=proof.nonce, instructions=instructions
    )


@router.post(
    "/{target_id}/verification/{proof_id}/check",
    status_code=202,
)
async def check_verification(
    target_id: uuid.UUID,
    proof_id: uuid.UUID,
    account: AccountDep,
    session: SessionDep,
    queue: QueueDep,
) -> VerificationCheckResponse:
    await _target_or_404(session, account, target_id, "member")
    proof = await get_ownership_proof(session, proof_id)
    if proof is None or proof.target_id != target_id:
        raise HTTPException(status_code=404, detail="ownership proof not found")

    await queue.enqueue_job("verify_ownership_job", str(proof_id))
    return VerificationCheckResponse(proof_id=proof_id, status="checking")
