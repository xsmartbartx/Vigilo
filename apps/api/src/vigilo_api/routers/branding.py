"""`PUT`/`GET /v1/me/branding-profile` — Business-tier report white-labeling
(Phase 9). Gated on `entitlements(account.plan_id).white_label_allowed`,
the same boolean-gate `QuotaExceeded` pattern `share_links_allowed`
established in Phase 7.
"""

from __future__ import annotations

from fastapi import APIRouter

from vigilo_api.audit_log import record
from vigilo_api.deps import AccountDep, ActiveOrgDep, SessionDep
from vigilo_api.schemas import BrandingProfileResponse, BrandingProfileUpdate
from vigilo_billing import QuotaExceeded, entitlements
from vigilo_identity.repository import get_branding_profile_for_org, upsert_branding_profile

router = APIRouter(prefix="/v1/me/branding-profile", tags=["branding"])


def _to_response(profile) -> BrandingProfileResponse:
    return BrandingProfileResponse(
        logo_url=profile.logo_url if profile else None,
        primary_color=profile.primary_color if profile else None,
        footer_text=profile.footer_text if profile else None,
        custom_domain=profile.custom_domain if profile else None,
    )


@router.put("")
async def update_branding_profile(
    body: BrandingProfileUpdate, account: AccountDep, org: ActiveOrgDep, session: SessionDep
) -> BrandingProfileResponse:
    org.require("admin")
    if not entitlements(org.plan_id).white_label_allowed:
        raise QuotaExceeded("white-label branding is not included in the account's plan")

    changes = body.model_dump(exclude_unset=True)
    profile = await upsert_branding_profile(session, account.id, org_id=org.org_id, **changes)
    await record(
        session, account, org.org_id, "branding_updated", "branding", fields=sorted(changes)
    )
    return _to_response(profile)


@router.get("")
async def get_account_branding_profile(
    org: ActiveOrgDep, session: SessionDep
) -> BrandingProfileResponse:
    profile = await get_branding_profile_for_org(session, org.org_id)
    return _to_response(profile)
