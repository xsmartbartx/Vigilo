from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vigilo_api.errors import handle_structured_error
from vigilo_api.routers import (
    accounts,
    api_keys,
    audit,
    badge,
    billing,
    branding,
    internal,
    monitors,
    orgs,
    public_api,
    reports,
    scans,
    share_links,
    suppressions,
    targets,
)
from vigilo_core.config import config
from vigilo_core.errors import StructuredError
from vigilo_core.observability import init_error_tracking

app = FastAPI(
    title="Vigilo API",
    description="Control-plane HTTP surface.",
    version="0.1.0",
)

init_error_tracking("api")  # off unless SENTRY_DSN is set

app.add_exception_handler(StructuredError, handle_structured_error)

# apps/web is the first browser client to ever call this API (Phase 4) — the
# PDF-export/report/share-link routes are called directly from client
# components. Conditional on WEB_APP_URL being set, same "works without it"
# resilience pattern as Clerk/Postmark's config.
_web_app_url = config().web_app_url
if _web_app_url:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[_web_app_url, *config().additional_cors_origins],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(scans.router)
app.include_router(targets.router)
app.include_router(accounts.router)
app.include_router(orgs.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(share_links.router)
app.include_router(billing.router)
app.include_router(billing.plans_router)
app.include_router(monitors.router)
app.include_router(badge.router)
app.include_router(api_keys.router)
app.include_router(branding.router)
app.include_router(suppressions.router)
app.include_router(public_api.router)
app.include_router(internal.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    cfg = config()
    return {
        "product": cfg.brand.brand.name,
        "env": cfg.env,
        "api_version": app.version,
        "registry_version": "unreleased",
        # The git commit this image was built from (build arg GIT_SHA); "unknown" when the
        # build did not pass one. Lets anyone tell what is actually running.
        "commit": os.environ.get("GIT_SHA") or "unknown",
    }
