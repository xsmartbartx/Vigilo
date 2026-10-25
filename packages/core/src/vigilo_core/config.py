"""Configuration and brand token loading. `config()` is the single entry point
every module uses to read brand identity and infrastructure settings
(docs/modules.md §1). Brand identity is always sourced from `brand.config.json`
— see README.md "Branding": nothing hardcodes the product name in source.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from vigilo_core.errors import ErrorCode, StructuredError

# Loads .env into the process environment if present, without overriding
# variables the environment (or CI) has already set. Phase 0-2 never needed
# this — nothing read DATABASE_URL/REDIS_URL/etc. at runtime. Phase 3's
# control plane does, so `uv run uvicorn ...` / `uv run arq ...` following
# README's "cp .env.example .env" instructions now actually picks it up.
load_dotenv()


class BrandTheme(BaseModel):
    colorPrimary: str
    colorAccent: str
    colorCritical: str
    colorHigh: str
    colorMedium: str
    colorLow: str
    colorPass: str
    fontSans: str
    fontMono: str


class Brand(BaseModel):
    name: str
    legalName: str
    slug: str
    domain: str
    tagline: str
    shortDescription: str
    supportEmail: str
    abuseEmail: str
    securityEmail: str


class BrandConfig(BaseModel):
    brand: Brand
    namespaces: dict[str, str] = Field(default_factory=dict)
    theme: BrandTheme | None = None


class Config(BaseModel):
    env: str = "development"
    brand: BrandConfig
    database_url: str | None = None
    redis_url: str | None = None
    object_store_endpoint: str | None = None
    object_store_access_key: str | None = None
    object_store_secret_key: str | None = None
    object_store_bucket: str | None = None
    clerk_secret_key: str | None = None
    clerk_jwks_url: str | None = None
    postmark_server_token: str | None = None
    mail_from_address: str | None = None
    web_app_url: str | None = None
    # Extra origins allowed to call the API beyond web_app_url itself (e.g.
    # apps/web served under a second, brand-owned domain alongside its
    # primary one) — CORS only, never used as the PDF-render navigation
    # target web_app_url is.
    additional_cors_origins: list[str] = []
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    # Required when the API key is not scoped to an Anthropic workspace: sent as
    # the `anthropic-workspace-id` header (Console -> Settings -> Workspaces).
    anthropic_workspace_id: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_id_pro: str | None = None
    stripe_price_id_pro_yearly: str | None = None
    # Optional: a specific Customer Portal configuration (bpc_...); Stripe's
    # default configuration is used when unset.
    stripe_portal_configuration_id: str | None = None
    # Shared with NEXORA Core (its NEXORA_SYNC_SECRET): signs the plan updates Core sends
    # for an organisation it bills. Unset = POST /v1/internal/org-plan is disabled (404).
    nexora_sync_secret: str | None = None
    # Where an organisation billed by Core is sent to manage its plan.
    nexora_console_billing_url: str = "https://console.onenexora.com/billing"


def _default_brand_config_path() -> Path:
    override = os.environ.get("VIGILO_BRAND_CONFIG_PATH")
    if override:
        return Path(override).expanduser().resolve()

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "brand.config.json"
        if candidate.is_file():
            return candidate

    raise StructuredError(
        ErrorCode.CONFIGURATION_ERROR,
        "brand.config.json not found in any parent directory; "
        "set VIGILO_BRAND_CONFIG_PATH explicitly",
    )


def _load_brand_config(path: Path) -> BrandConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StructuredError(
            ErrorCode.CONFIGURATION_ERROR, f"brand config not found at {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise StructuredError(
            ErrorCode.CONFIGURATION_ERROR, f"brand config at {path} is not valid JSON"
        ) from exc

    return BrandConfig.model_validate(raw)


@lru_cache(maxsize=1)
def config() -> Config:
    """Load and cache process configuration. Call `config.cache_clear()` in
    tests that need to reload after changing environment variables."""
    brand_path = _default_brand_config_path()
    brand = _load_brand_config(brand_path)

    return Config(
        env=os.environ.get("ENV", "development"),
        brand=brand,
        database_url=os.environ.get("DATABASE_URL"),
        redis_url=os.environ.get("REDIS_URL"),
        object_store_endpoint=os.environ.get("OBJECT_STORE_ENDPOINT"),
        object_store_access_key=os.environ.get("OBJECT_STORE_ACCESS_KEY"),
        object_store_secret_key=os.environ.get("OBJECT_STORE_SECRET_KEY"),
        object_store_bucket=os.environ.get("OBJECT_STORE_BUCKET"),
        clerk_secret_key=os.environ.get("CLERK_SECRET_KEY"),
        clerk_jwks_url=os.environ.get("CLERK_JWKS_URL"),
        postmark_server_token=os.environ.get("POSTMARK_SERVER_TOKEN"),
        mail_from_address=os.environ.get("MAIL_FROM_ADDRESS"),
        web_app_url=os.environ.get("WEB_APP_URL"),
        additional_cors_origins=[
            origin.strip()
            for origin in os.environ.get("ADDITIONAL_CORS_ORIGINS", "").split(",")
            if origin.strip()
        ],
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        # `or`, not a get() default: compose passes an unset variable as "".
        anthropic_model=os.environ.get("ANTHROPIC_MODEL") or "claude-haiku-4-5",
        anthropic_workspace_id=os.environ.get("ANTHROPIC_WORKSPACE_ID") or None,
        stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET"),
        stripe_price_id_pro=os.environ.get("STRIPE_PRICE_ID_PRO"),
        stripe_price_id_pro_yearly=os.environ.get("STRIPE_PRICE_ID_PRO_YEARLY"),
        stripe_portal_configuration_id=os.environ.get("STRIPE_PORTAL_CONFIGURATION_ID"),
        nexora_sync_secret=os.environ.get("NEXORA_SYNC_SECRET") or None,
        nexora_console_billing_url=os.environ.get("NEXORA_CONSOLE_BILLING_URL")
        or "https://console.onenexora.com/billing",
    )
