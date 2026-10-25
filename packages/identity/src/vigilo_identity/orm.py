"""AccountRow — the tenant root (docs/prooflight-vision-and-architecture.md §6.1).

`clerk_user_id` is a deliberate addition beyond the domain-model table: the
mapping from Clerk's user id to a local `Account` row. It is nullable because
a free scan creates an `Account(status="anonymous")` from an email address
alone, before anyone has signed in — see `get_or_create_account`.

`SubscriptionRow` (Phase 7), `ApiKeyRow` and `BrandingProfileRow` (both
Phase 9) all live here, not in their own packages — each is account-scoped
auxiliary state with no more natural a home than `AccountRow` itself,
matching `Subscription`'s own placement rationale (`packages/billing`
stays ORM-free by design, docs/modules.md §11).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from vigilo_persistence.base import Base


class AccountRow(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="anonymous")
    plan_id: Mapped[str | None] = mapped_column(String(64), default=None)
    data_region: Mapped[str | None] = mapped_column(String(32), default=None)
    clerk_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    plan_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(32))
    # Not unique on account_id alone — a provider issues a new subscription
    # id on plan change/renewal, so an account can accumulate more than one
    # row over time; upsert_subscription() keys its upsert on this field,
    # get_subscription_by_account() picks the most recent.
    provider_subscription_id: Mapped[str] = mapped_column(String(128), unique=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    product_slug: Mapped[str] = mapped_column(String(32), default="vigilo", server_default="vigilo")
    billing_interval: Mapped[str] = mapped_column(
        String(8), default="month", server_default="month"
    )
    # Creation time of the last provider event applied to this row; an older
    # event delivered later (webhooks are not ordered) is ignored.
    provider_event_created: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    # The customer asked to cancel; access runs until `current_period_end`.
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKeyRow(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    prefix: Mapped[str] = mapped_column(String(16))
    # sha256 hex digest — the plaintext key is generated once, returned to
    # the caller, and never stored anywhere (matches create_share_link()'s
    # token-hashed-at-rest precedent).
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    scopes: Mapped[list] = mapped_column(JSON)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrandingProfileRow(Base):
    __tablename__ = "branding_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # The account that last saved the profile; the profile itself belongs to
    # the organisation (one per org).
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, index=True
    )
    logo_url: Mapped[str | None] = mapped_column(String(500), default=None)
    primary_color: Mapped[str | None] = mapped_column(String(16), default=None)
    footer_text: Mapped[str | None] = mapped_column(String(500), default=None)
    custom_domain: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clerk_org_id: Mapped[str | None] = mapped_column(String(128), unique=True, default=None)
    # The Stripe customer this organisation pays as: one per organisation.
    billing_customer_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, default=None
    )
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(48), unique=True)
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MembershipRow(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("org_id", "account_id", name="uq_memberships_org_id_account_id"),
        Index(
            "uq_memberships_one_owner_per_org",
            "org_id",
            unique=True,
            postgresql_where=text("role = 'owner'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductEnablementRow(Base):
    __tablename__ = "product_enablements"
    __table_args__ = (
        UniqueConstraint("org_id", "product_slug", name="uq_product_enablements_org_product"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    product_slug: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="enabled")
    enabled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsageCounterRow(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "product_slug", "meter", "period_start", name="uq_usage_counters_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    product_slug: Mapped[str] = mapped_column(String(32))
    meter: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[date] = mapped_column(Date)
    count: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrgInviteRow(Base):
    __tablename__ = "org_invites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(16))
    # sha256 hex digest; plaintext returned once at creation (same pattern as api_keys).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), default=None
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CoreOrgPlanRow(Base):
    """The plan NEXORA Core last sent for a Clerk organisation, kept even when no Vigilo
    organisation is linked to it yet, and applied when one is."""

    __tablename__ = "core_org_plans"

    clerk_org_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
