"""`GET /v1/me` — the first call after a Clerk sign-in. `require_account`
auto-provisions the `Account` (and links it to an earlier anonymous account
created by a free scan under the same email, if one exists).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vigilo_api import account_deletion
from vigilo_api.deps import AccountDep, SessionDep
from vigilo_api.schemas import AccountResponse, EntitlementsResponse
from vigilo_billing import entitlements
from vigilo_integrations import (
    delete_clerk_user,
    delete_evidence_bundle,
    delete_report_pdf,
)
from vigilo_integrations.errors import IdentityProviderError, ObjectStoreError
from vigilo_security.audit import AuditEvent, audit

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["accounts"])


@router.get("/me")
async def get_me(account: AccountDep) -> AccountResponse:
    return AccountResponse(
        account_id=account.id,
        email=account.email,
        status=account.status,
        created_at=account.created_at,
        entitlements=EntitlementsResponse.model_validate(entitlements(account.plan_id)),
    )


class DeletionBlockerResponse(BaseModel):
    kind: str
    org_id: uuid.UUID
    org_name: str
    detail: str


class DeletionCheckResponse(BaseModel):
    blockers: list[DeletionBlockerResponse]


class DeleteAccountRequest(BaseModel):
    confirm_email: str


class DeleteAccountResponse(BaseModel):
    deleted: bool
    # Whether the sign-in identity was also removed at the identity provider.
    identity_removed: bool
    # "complete", "partial" (some stored files could not be removed) or "skipped".
    storage_cleanup: str


@router.get("/me/deletion-check")
async def check_account_deletion(account: AccountDep, session: SessionDep) -> DeletionCheckResponse:
    """What must be done before this account can be deleted (may be nothing)."""
    blockers = await account_deletion.deletion_blockers(session, account)
    return DeletionCheckResponse(blockers=[DeletionBlockerResponse(**b.__dict__) for b in blockers])


@router.post("/me/delete")
async def delete_my_account(
    body: DeleteAccountRequest, account: AccountDep, session: SessionDep
) -> DeleteAccountResponse:
    """Permanently delete the signed-in account and the data that is theirs
    (see `vigilo_api.account_deletion`). The caller must type their own email."""
    if body.confirm_email.strip().lower() != account.email.lower():
        raise HTTPException(status_code=422, detail="the email does not match this account")

    blockers = await account_deletion.deletion_blockers(session, account)
    if blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ACCOUNT_DELETION_BLOCKED",
                "message": "Finish these first, then try again.",
                "blockers": [b.detail for b in blockers],
            },
        )

    result = await account_deletion.delete_account(session, account)
    await audit(
        session,
        AuditEvent(
            actor=str(account.id),
            action="account_deleted",
            subject="account",  # no address: the record must not keep what was erased
            account_id=account.id,
            metadata={"organisations_deleted": len(result.org_ids)},
        ),
    )
    await session.commit()  # the data is gone for good before anything outside is touched

    storage = "skipped"
    if result.bundle_ids or result.report_ids:
        storage = "complete"
        for bundle_id in result.bundle_ids:
            try:
                await delete_evidence_bundle(bundle_id)
            except ObjectStoreError:
                storage = "partial"
                _log.error("account deletion: could not remove an evidence bundle")
        for report_id in result.report_ids:
            try:
                await delete_report_pdf(str(report_id))
            except ObjectStoreError:
                storage = "partial"
                _log.error("account deletion: could not remove a report file")

    identity_removed = False
    if account.clerk_user_id:
        try:
            await delete_clerk_user(account.clerk_user_id)
            identity_removed = True
        except IdentityProviderError:
            _log.error("account deletion: could not remove the sign-in identity")

    return DeleteAccountResponse(
        deleted=True, identity_removed=identity_removed, storage_cleanup=storage
    )
