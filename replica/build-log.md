# Build log

| ID | date | status | missing / notes |
| --- | --- | --- | --- |
| design primitives | 2026-10-07 | done | Button, Input, Badge, Card, EmptyState, UsageMeter, ProductTile on /design |
| S21 launcher /console | 2026-10-07 | partial | fake data layer (lib/nexora/data.ts); no enable action; no loading/error states yet |
| S25 usage /console/usage | 2026-10-07 | partial | fake data; empty state built |
| S22 members /console/members | 2026-10-07 | partial | read-only; invite, role change, remove need backend |
| S02 products /products | 2026-10-07 | partial | index only; no per-product pages, no category filter |
| S04 pricing /pricing | 2026-10-07 | done | no checkout links yet (needs org billing) |
| S20 org switcher | - | not started | needs organizations backend |
| S01 home | 2026-10-08 | done, not rendered | `/` is now the Nexora platform home; the Vigilo scan landing moved to `/products/vigilo` |

Not verified: no screenshots or 390/1440 checks. `.env` has empty Clerk keys, so the dev server returns 500 on every route. Lint, tsc and `next build` (placeholder Clerk env) pass. No replica/clone-screens/ yet.
Harder than expected: the vertical slice's tenancy half (sign up -> personal org) is backend work, so only the UI half exists.

## 2026-10-07 fix-plan pass (replica/fixes.md items 1-4)
| item | status | notes |
| --- | --- | --- |
| 1 Fix these first | done, not rendered | `components/report/FixFirst.tsx`; hidden at 3 or fewer open findings; logic exercised by a script |
| 2 Stack-aware why line | partial | migration 0011 `scans.stack`; reporting/context.py; 4 families of sentences; scans before 0011 have no stack |
| 3 Team risk acceptance | done | `vigilo_api/access.py`, suppression routes, report `can_accept_risk`; PDF/share/monitoring still owner-only |
| 4 Supabase RLS guide | done | reporting/guides.py for VG-DAT-002 (template path only) |
| 5 App-context questions | not built | speculative, L |
Verified: ruff, 13 new Python tests, `alembic check` clean with 0011, web lint/tsc/build. Not verified: any browser rendering.

## 2026-10-07 org-scoped reads
Migrations 0012 (one project and one branding profile per org). Routers: targets, monitors, share links, reports, suppressions, API keys, branding, public API. Web: org id sent on list/create calls, dashboard shows the switcher and the org's plan, role-based disabling of add/edit/keys. Verified: 711 Python tests pass (4 MinIO failures unchanged), `alembic check` clean, 0012 up/down on populated data, web lint/tsc/build. Not verified: any browser rendering.

## 2026-10-08 per-org billing
Migration 0013. Checkout, portal, webhook and plan lookup per organisation; billing page shows and changes the active org's plan, owner/admin only. Verified: 723 Python tests pass (4 MinIO failures unchanged), `alembic check` clean, 0013 up/down, web lint/tsc/build. Not verified: real Stripe (test mode needs your keys and the org metadata path end to end), any browser rendering.

## 2026-10-08 invite and role UI
Backend: list/withdraw pending invites, one open invite per address (a new one replaces the old link), inviting an existing member is a 409, members can leave. Web: /console/members (roles, remove, invite form, pending list, leave) and /invite/[token]. Invites are shared as a link shown once; no email is sent (needs Postmark + a rate limit first). Verified: 4 new API tests + 1 updated, ruff, web lint/tsc/build. Not verified: browser rendering, keyboard use, the Clerk sign-in round trip back to /invite/[token].

## 2026-10-08 invite emails
Postmark delivery for invitations plus resend, with per-org, per-inviter and per-recipient limits and fail-closed behaviour. UI shows what happened to the email. Verified: 9 new tests (736 total pass, 4 MinIO failures unchanged), ruff, web lint/tsc/build. Not verified: a real Postmark send, deliverability (SPF/DKIM on the sending domain), browser rendering.

## 2026-10-08 home and product pages
S01 `/` Nexora home (hero with three CTAs, shared platform, products, how it works). S02 `/products` with category filter. S03 `/products/[slug]` template for Sentinel, CSPM, Gateway, NeuraWall (headline, summary, how it fits, plans) and `/products/vigilo` (the previous landing with the scan form). Pricing page moved into the same shell. Report, share and monitoring headers now link to `/products/vigilo`. Specs extended (28 total, skipped without Clerk keys). Verified: lint, tsc, `next build`. Not verified: rendering, links in a browser, axe.
Decisions to confirm: the platform name lives in `lib/nexora/platform.ts` (not `brand.config.json`) pending the Nexora trademark question; product-page copy mirrors the one-line descriptions on onenexora.com and claims nothing more, but those four engines are not in this repo, so the pages describe products this build cannot run.

## 2026-10-08 cross-product billing view
Backend summary endpoint, cancellation capture (0014), `BillingOverview` on the billing page above the Vigilo plan table. Verified: 6 new tests (742 total pass, 4 MinIO failures unchanged), `alembic check` clean, 0014 up/down, ruff, web lint/tsc/build. Not verified: browser rendering, real Stripe cancellation events (the `cancel_at_period_end` field name follows Stripe's documented subscription object but was not observed live).

## 2026-10-08 audit log
Migration 0015, ~20 new recorded actions, org read API, `/console/audit` with nav link. Verified: 8 new tests (750 total pass, 4 MinIO failures unchanged), `alembic check` clean, 0015 on populated audit table with the append-only trigger still enforced, ruff, web lint/tsc/build, label sentences exercised by script. Not verified: browser rendering.

## 2026-10-09 pre-deploy fixes (option A)
Account deletion (backend, account page, signed-out page), placeholder favicon/apple icon/social images, optional Sentry hook, self-hosting and API docs corrected, Next.js upgraded to 16.4.0 for a critical advisory. Verified: 17 new Python tests (765 pass, 4 MinIO failures unchanged), ruff, `alembic check` and 0016 on populated data, web lint/tsc/build, production npm audit clean, generated images viewed. Not verified: browser rendering of the account page, a real Clerk deletion, a real Sentry event.

## 2026-10-09 first real browser run (Clerk dev keys)
Keys landed via `clerk link` and `clerk env pull` (the CLI wrote `CLERK_PUBLISHABLE_KEY`, not the `NEXT_PUBLIC_` name the app reads; mapped in `.env`, JWKS URL derived from the publishable key and checked: 200). Public-page specs: first run 6 pass / 8 fail; causes: Next dev blocked `127.0.0.1` (HMR and hydration, so client components such as the billing toggle did nothing: fixed with `allowedDevOrigins`), one ambiguous `getByText("Live")` in the spec, and a real accessibility bug: the footer copyright and other grey text at 2.84:1 contrast (AA needs 4.5): raised `text-black/30|40|50` (and dark equivalents) to AA across 17 files. Now 28/28 pass on desktop and mobile. Preview-launched dev servers hung in this environment; the API and web were started from the shell and by Playwright instead.
Blocked: signed-in specs need a Clerk test user and the `vigilo-api` JWT template; the dev instance has neither.

## 2026-10-09 option B: signed-in browser run (real Clerk dev instance)
Setup: JWT template `vigilo-api` created through the Clerk API (with permission); the test user signed up by the person themselves at /sign-up (I do not create accounts); Playwright signs in with `@clerk/testing` using only the email (`E2E_USER_EMAIL`, never stored in the repo). Browser tests get their own database `vigilo_e2e` because pytest wipes `vigilo` on every run (it wiped my first dev data): `scripts/e2e-up.sh` / `e2e-down.sh` / `e2e-reset-db.sh`. Servers started through the preview tool hung here, so the API and worker run from the shell and Playwright starts the web app.
Result: 85 passed, 9 skipped (mutating specs are desktop-only). Specs: `public-pages`, `signed-in`, `signed-in-scan` (a real scan through the worker to a report).
Bugs found and fixed:
1. **First sign-in returned a 500** for every new person: the console page and its layout call the API at once and the two account inserts collided on the unique Clerk id. Fixed in `get_or_create_account` (savepoint, loser reads the winner's row); regression test proven to fail without the fix.
2. Footer and other grey text at 2.84:1 contrast on every page (AA is 4.5): raised across 17 files.
3. Severity badges (white on orange/yellow/cyan) and the brand cyan used as text failed contrast on reports: severity and accent colours moved to AA-safe values in `globals.css` and `brand.config.json`, with lighter text variants in dark mode and separate badge fills; prompt-block label/button darkened.
4. Client components never hydrated on 127.0.0.1 in dev (Next blocked it): `allowedDevOrigins`.
5. Console header overflowed at 390px (seven links in one row): navigation wraps. Page containers shrink-wrapped their content in the flex body: `w-full`. The org switcher grew with the longest organisation name: width-capped. A visually hidden table header at the end of a wide table leaked into the page's scroll width: scroll containers are now positioned. Scrollable tables are keyboard-focusable regions.
6. "Still scanning..." told people to refresh by hand: the page now refreshes itself (tested without a reload).
7. Accepted risks never showed the reason they were accepted with: owners now see it.
Spec fixes (not product bugs): ambiguous text matches, Next's own `role=alert` route announcer, a disabled button, free-plan limits making specs non-repeatable (specs create what they need; the database is reset per run).
Not run: second-person invite acceptance (needs a second Clerk user), real Stripe/Postmark, PDF export, share links and monitoring (Pro plan), real account deletion.

## 2026-10-09 remaining must-haves
Scored 7 -> 12 of 13 must-haves (parity 63.6 -> 77.3), each backed by evidence now:
- **Quotas per product**: the monthly scan quota was a rolling 30-day count of scan jobs while the Usage page showed a calendar-month counter, so a person could be told "2 of 3" and be refused (or the reverse). Both submission paths now enforce the same per-organisation calendar-month counter, using the organisation's own plan. Tests: month boundary, a paying org, the public API, and the number matching the Usage page.
- **Browser coverage** for organisations, the switcher, roles and the launcher (`signed-in-teams.spec.ts`): a second member is inserted into the throwaway test database (not an identity anywhere), so role change and removal run in a real browser; switching organisations keeps targets and enabled products apart; Enable is audited. A race in my own helper (the select changes before the server applies the switch) taught the specs to wait for the server action.
- Signed-in specs now run with one worker: they share one Clerk user, one database and per-user cookies; in parallel they produced 4 spurious failures and Clerk API errors.
- Statuses moved from `partial` to `yes` for the toggle, quotas, members/roles, organisations/switcher and the launcher, with the exact limits of each claim in `features.csv`.
Still open: **single sign-on across products**. One Clerk sign-in covers the console, Vigilo, the dashboard and the API. The other products' engines are separate projects (siblings of this folder, not opened) and are not connected, so cross-product sign-on is unproven. Honest choices: connect them to this Clerk app, or change the scope in `features.csv` to the one product that exists.
Suite: 90 browser specs pass (14 skipped by design), 769 Python tests pass, 4 object-storage tests unconfirmed (MinIO image cannot be pulled here).

## 2026-10-09 scope: the one product that exists
Chosen by the owner (option 2). Changes: the four other products are "Coming soon" in the catalog, launcher, pricing and product pages; `AVAILABLE_PRODUCTS = ("vigilo",)` makes the API refuse enabling anything else (409 `not_available`; one constant to change when an engine connects; tests cover both states); the launcher shows "Not open yet" with a link to what is planned; five matrix rows became `skip` and the SSO row now says what exists. Parity 77.3 -> 89.8, and `parity.md` states that this jump is rescoping, not features. 90 browser specs pass (launcher spec rewritten), Python suite green apart from the 4 MinIO tests.

## 2026-10-09 ownership transfer
Built and verified (10 API tests, 1 browser spec; 91 browser specs pass, 15 skipped by design; 780 Python tests pass, 4 MinIO tests unconfirmed). Found: the usage endpoint used the owner's personal plan instead of the organisation's. Also: a live Stripe key reached `.env` (see deploy.md); the e2e scripts now blank Stripe settings so tests cannot touch real Stripe. The Stripe test-mode run is still waiting for a `sk_test_` key.

## 2026-10-09 CI for object storage and the browser suite
`test` job starts moto instead of the unpullable MinIO image; new `e2e` job runs the Playwright suite against Postgres, Redis, moto, the API and the worker, gated on three Clerk secrets (`E2E_CLERK_PUBLISHABLE_KEY`, `E2E_CLERK_SECRET_KEY`, `E2E_USER_EMAIL`). `apps/web/e2e/db.ts` now uses the `pg` driver (no docker/psql). Verified locally: 784 Python tests pass with moto; browser suite 91 passed, 15 skipped on a fresh DB with only the workflow's env. Not verified: the workflow on GitHub. The self-host compose still references MinIO from quay.

## 2026-10-09 trust page
`/trust` built from verified code facts only (egress guard, ownership verification, redaction, 90-day evidence, SHA-256 key and token hashes, per-org rate limits, append-only audit log, self-serve deletion); says plainly there is no SOC 2/ISO report or pen test. Footer link; spec F01-H9 with axe passes (30 public-page tests). Still carries the draft-legal banner.

## 2026-10-09 product-scoped API keys
Scopes are now `product:resource:action` (`vigilo:scan:run`). New keys are stored qualified; bare legacy scopes on existing keys are normalised at check and list time, so no migration or key reissue. Unknown-product scopes return 422. UI offers the qualified scopes. 3 new tests; 786 Python tests pass with moto. docs/api.md updated. README line left on the short form.

## 2026-10-08 browser suite rerun
93 passed, 15 skipped by design (6.0 min) after the trust page and product-scoped keys. Four earlier full runs stalled or timed out in sign-in, page loads and the scan report page with no code failure; the same suite passed once the machine was kept awake with `caffeinate -d -i -s`. A display set to sleep after 2 minutes is the likely cause (headless Chromium is throttled when the display sleeps), not proven. On macOS run: `caffeinate -d -i -s npx playwright test`. `e2e/auth.ts` sign-in now waits for `domcontentloaded` instead of `load`.

## 2026-10-08 Stripe setup script
`uv run python scripts/stripe_setup.py --mode test|live [--apply] [--webhook-url URL]`: creates the Vigilo Pro product, monthly ($29) and yearly ($290) prices (amounts read from the app's plan so they cannot drift), the portal configuration (cancel at period end, monthly/yearly switch, invoices) and optionally the webhook endpoint. Dry run by default; idempotent (lookup keys and metadata); refuses a mode that does not match the key; reads the key from the environment only. 6 tests against a fake Stripe. Not run against real Stripe: no test key was provided. A live key was found in `.env.example` (uncommitted, never pushed) and removed.

## 2026-10-09 Stripe live objects created (by the owner, in their own shell)
`stripe_setup.py --mode live --apply` created: product `prod_VPUM7rHTaNOABJ`, monthly price `price_1UOfNwDimAgl5dOBTvKitHMZ` ($29/mo), yearly price `price_1UOfNxDimAgl5dOBMzk5gfOd` ($290/yr), portal configuration `bpc_1UOfNxDimAgl5dOBcdbPf6PT`. Webhook endpoint not created yet (needs the production API domain). No real purchase tested yet. Production env only, not local `.env`: `STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_PRO_YEARLY`, `STRIPE_PORTAL_CONFIGURATION_ID`.

## 2026-10-09 security contact
`/.well-known/security.txt` (RFC 9116) served by a route handler: Contact is the brand security address (`security@onenexora.com`), Expires is a rolling year, Canonical and Policy use `WEB_APP_URL`. The trust page now shows the security address for vulnerability reports instead of support. Needs the `security@` mailbox to exist before launch (see dns.md). Typecheck and lint clean; served 200 text/plain in dev.

## 2026-10-09 smoke script
`scripts/smoke.sh <web-url> <api-url>`: read-only post-deploy checks (health, home, pricing, trust, security.txt, aup, sign-in, unauthenticated API gives 401, certificates valid 14+ days). Exits 1 on any failure. Checked only against unrelated hosts here (it correctly fails); not yet run against the real deployment.

## 2026-10-09 last could-haves out of scope
Bundle discounts and Marketplace/Labs/Solutions marked `skip` with reasons. Parity now 100 / 100 because nothing counted is missing; this is rescoping, not new features (see parity.md).

## 2026-10-09 browser suite rerun
93 passed, 15 skipped by design, 0 failed (5.0 min), run under `caffeinate -d -i -s` against the local stack (real Clerk dev instance, API, scanner worker, Postgres, moto). Covers the changes since the last run: product-scoped API keys, the trust page and security.txt route, the onenexora.com address and User-Agent changes, the scripts and docs. Same count as the 2026-10-08 passing run (93 passed, 15 skipped).

## 2026-10-09 Postmark skipped
Owner chose to launch without transactional email. Checked in code: all three senders (invite emails, monitoring notifications, scan-report job) catch `MailDeliveryFailed`, and invitations return `email_status: not_configured` with the link still in the response. Consequences: no emailed invitations (share the link by hand), no emailed monitoring alerts or scan reports. No SPF/DKIM/DMARC records were added.

## 2026-10-09 privacy wording matches "no email"
`/privacy` no longer says results are emailed, that invitations are emailed, or that an email provider is a subprocessor; it says none of that is sent now and that the policy will be updated before any email is. Last-updated date set to October 2026. The invite UI already shows "email sending is not set up here. Send them this link yourself." for `not_configured`. Typecheck and lint clean; still carries the draft-legal banner.

## 2026-10-09 browser suite rerun after the privacy wording change
93 passed, 15 skipped by design, 0 failed (6.0 min), under `caffeinate -d -i -s` against the local stack (real Clerk dev instance, API, scanner worker, Postgres, moto). Covers the privacy page rewrite (no emailed results or invitations, no email subprocessor), the Postmark skip and the DNS/Caddy docs. Same counts as the previous two passing runs.

## 2026-10-09 server setup script
`scripts/vps_setup.sh`: one-shot first-time setup for the VPS, run by the owner on the server. Hidden prompts for secrets with prefix checks (wrong prefix is rejected), generated internal passwords, awk-based env writer that keeps any character in a value, mode 600, external-proxy mode, port 3000/8000 check, compose up, migrations, prints the Caddy blocks. Verified in a temp copy with `--no-start` and fake inputs (prefix rejection, special characters in a secret, file mode). The Docker start path is untested.

## 2026-10-10 merge of origin/main into deploy-prep (option 1)
Merged `origin/main` (27 commits) keeping this branch's organisation and billing design. Dropped the upstream Clerk-Organizations/NEXORA Core billing work: `core_sync.py`, `routers/internal.py`, `test_core_sync.py`, both `test_org_accounts.py`, migration `0009_org_accounts`, `docs/org-accounts.md`, the `NEXORA_SYNC_SECRET` env and compose lines, and upstream's edits to auth/deps/billing/identity/config/jobs. Kept: Dependabot bumps (Next stays 16.4.0, the version that fixes the critical advisory), the GitHub Action PR comment and its tests, the CI Caddyfile-validate job, the license, the s3mock compose images. Web host is `vigilo.onenexora.com` (brand domain, scanner User-Agent now `/aup`, SARIF URI). Hand fixes: CI test job back on moto :9000, half-merged `dashboard/layout.tsx`. Result on the merged tree: 801 Python tests passed, ruff clean, web typecheck/lint/build clean, browser suite 93 passed, 15 skipped by design, 0 failed (5.0 min, under caffeinate). Nothing pushed. Open: the compose s3mock stand-in does not check credentials (internal network only); the API hostname; DNS record `vigilo` -> 92.5.69.99.

## 2026-10-10 production deploy
Deployed `a45294c` (main with PR #10) to the shared host through `/opt/nexora/infrastructure/deployment/deploy.sh vigilo api web scanner`, after a backup (`vigilo-backup-20261010T135725Z.tar.gz`, 30 KB, copied to the owner's Mac). That script pulls and restarts but does not migrate, so the migration was run separately: `0009 -> 0017` applied without errors (production was at upstream's `0009_org_accounts`; this repo's organisation migrations now follow it as 0010-0017). Smoke check against `https://vigilo.onenexora.com` and `https://vigilo-api.onenexora.com`: all 10 checks passed. Found before migrating: one org-owned test account (created 2026-10-04, free plan, owns 1 project), which now has an unused personal organisation; its project is intact but not reachable in the app. Not yet done: a real sign-in and scan on production, the purchase-and-refund check, the Stripe price-set decision, the four mailboxes.

## 2026-10-10 uptime check
`.github/workflows/uptime.yml`: GitHub Actions runs `scripts/smoke.sh` against `https://vigilo.onenexora.com` and `https://vigilo-api.onenexora.com` every 10 minutes, with one retry after 60 seconds; a failed run emails the person who last edited the workflow. No new account or cost. Limits: GitHub's scheduler is best-effort and disables scheduled workflows after 60 days without repository activity; it tests from GitHub's network, so it does not replace host-level monitoring (disk, memory, container restarts). Not yet run on GitHub.

## 2026-10-11 anonymous scan throttle (found by a route-auth audit)
Audit of all 65 API routes: 11 have no auth dependency; 9 are public by design (health, version, plans, badge, Stripe webhook which verifies its signature, share links by token, scan status and report/PDF by unguessable id, and the free scan itself). One was a real gap: `POST /v1/scans` had no per-address or per-email limit, only a per-target 24-hour ceiling that does not apply to a new target, so a caller could submit unlimited different URLs. Added `scan_throttle.py`: fixed one-hour windows, 30 per address and 10 per email by default (`SCAN_RATE_PER_IP_PER_HOUR`, `SCAN_RATE_PER_EMAIL_PER_HOUR`, 0 = off), HTTP 429 with Retry-After. The address is the LAST X-Forwarded-For entry (the one our proxy appended), so a forged earlier entry does not help. 5 new tests; 806 Python tests pass. The test stack and the CI e2e job turn it off. Not deployed. Deploy note: the limit depends on the edge proxy appending the real client address; if the API were ever reached without a proxy it falls back to the socket peer.

## 2026-10-11 logo concepts
`replica/logo/`: three concept marks (A steady lens, B vigil V, C proof in the lens) as 64x64 SVGs plus a self-contained `preview.html` board (16/32/64/128 px, lockup, browser tab). Nothing shipped changes: `apps/web/app/icon.svg` is still the placeholder. Not yet done: owner pick, the 1024px no-transparency app icon, favicon set, 1200x630 social image, and the check against the logos of Nexora (Capterra), Vigilos and VigiloSec, which I cannot do from here. The name itself is still uncleared for trademark.

## 2026-10-11 dependency audit
`pip-audit` over the locked Python set (107 pins): no known vulnerabilities (Mako was bumped earlier for GHSA-5639-2j2p-m4mx). `npm audit --omit=dev` (production web dependencies): 0 vulnerabilities. Full `npm audit` still lists dev-only findings; none ship to production. The Python audit had not been run before today.

## 2026-10-11 production deploy: anonymous scan throttle
Backup first (`vigilo-backup-20261011T120309Z.tar.gz`, 36 KB). Deployed `8c76349` (main after #15, includes the throttle) with `deploy.sh vigilo api web scanner` at 12:06 UTC; no migration. Smoke check: all 10 checks passed. Not yet confirmed on production: the 429 itself (submitting scans from one address would create real scan jobs), so verify it with a few scans from one address when convenient. Default limits: 30 per address and 10 per email per hour.

## 2026-10-11 /version reports the running commit
`/version` gained `commit` (from the `GIT_SHA` build arg in `apps/api/Dockerfile` and the compose build args); `scripts/deploy.sh` exports it and `scripts/smoke.sh` prints it. 2 new tests; ruff clean. Production only reports it once the shared platform deploy script exports `GIT_SHA` (one line, in `replica/deploy.md`); until then the field says `unknown`. Not deployed.

## 2026-10-11 engine plan
`replica/engine-plan.md`: a draft plan for connecting another product engine, with the open decisions (who bills, which engine first, shared login). Nothing built.

## 2026-10-11 backups on a schedule, disk check, restore test
`scripts/install-backup-cron.sh` (daily backup at 03:00 with 14-day retention, disk check at 03:30; `--dry-run` supported) and `scripts/check-disk.sh` (non-zero at 85% by default). Both tested locally in dry-run and for exit codes; **not installed on the server** and not run there. A real restore test was done: the 2026-10-10 backup restored cleanly into a scratch Postgres (revision 0009, 5 accounts, 5 projects, 18 tables). Still open: nothing alerts on a high disk or a failed backup, and backups are not yet copied off the host.

## 2026-10-11 SonarCloud triage (xsmartbartx_Vigilo, 270 open issues at the time)
Fixed: both bugs (a floating promise in AcceptedRisksSection, a tautological assertion), 56 redundant `response_model` arguments (found by AST: identical to the return annotation; the OpenAPI schema is byte-identical before and after), 8 unpinned GitHub Actions now pinned to commit SHAs with a Dependabot config to refresh them (23 `uses:` lines), the malformed `noqa` comment, a redundant exception class, a nested conditional, consecutive appends, `[[` in two scripts, three `assert True` placeholder tests, a useless fixture yield, and a NOSONAR on the non-security jitter. 808 tests pass; ruff and web lint/typecheck clean. Deliberately not changed: the four BLOCKER "password in code" findings (test and compose default `vigilo-dev-secret` values, replaced by generated ones in production), containers running as root and `--no-build`/lockfile pin findings in Dockerfiles and CI (behavioural changes to the images or install steps, to be done deliberately), 46 "document this HTTPException in responses" (changes the published API docs), 29 "mark props readonly" and 13 JSX-spacing findings (style churn across ~35 files), and complexity and duplicated-literal refactors. Some Sonar line numbers are from an older analysis and were stale.

## 2026-10-11 uptime monitor was silently skipped after the repository changed owner
The scheduled run at 14:50 UTC showed `skipped`: the guard `github.repository == 'N3xora/Vigilo'` stopped matching once GitHub reported the repository as `xsmartbartx/Vigilo`, so the monitor had stopped checking. Replaced with `!github.event.repository.fork`, which does not depend on the owner name. Lesson: a monitor that skips looks like a monitor that passes; check the run list, not only the failure emails.

## 2026-10-11 production deploy of b0b1bc0
Backup first (`vigilo-backup-20261011T173950Z.tar.gz`, 36 KB), then `deploy.sh vigilo api web scanner` at 17:42 UTC: `b0b1bc0` (main after #22). Includes the `/version` commit field, the backup and disk-check scripts, the SonarCloud fixes, pinned GitHub Actions and the uptime-guard fix. No migration. Smoke check: all 10 checks passed. `/version` now returns `"commit": "unknown"`: the new build is live, and the shared platform deploy script still does not export `GIT_SHA`, so the commit is not shown yet (the Nexora-repo change in `deploy.md`). The scheduled backup job runs from tonight (03:00 server time).

## 2026-10-12 restored POST /v1/internal/org-plan (a regression I introduced)
Nexora's ADR-0014 (phase 4, shipped 2026-10-04) makes NEXORA Core the owner of Vigilo's organisation subscriptions: Core signs `{clerk_org_id, plan_id}` with HMAC-SHA256 (`NEXORA_SYNC_SECRET`) and POSTs it to `/v1/internal/org-plan`. Core's own smoke test (`F05-N`) expects 401 for an unsigned call. My merge of option 1 removed that endpoint and the compose passthrough of `NEXORA_SYNC_SECRET`, so production has answered 404 since the first deploy of that merge (2026-10-10), and Core's webhook would have failed (and Stripe retried) on any Vigilo plan change for an organisation. Restored on this branch: `core_sync.py` (signature, 5-minute replay window, constant-time compare), `routers/internal.py` (404 without a secret, 401 for any signature failure, 400 for a bad payload, 200 `ignored` for an organisation not linked here, 200 `applied` otherwise), `set_org_plan_from_core` (one subscription row per organisation, `nexora-core:<org id>`, idempotent; `free` closes it), the compose and env wiring, and a 409 from `/v1/billing/portal` for a Core-billed organisation pointing at NEXORA Console. 13 new tests; 821 pass. **Limit:** a plan is applied only to an organisation whose `organizations.clerk_org_id` matches Core's Clerk organisation, and nothing in this app sets that link yet, so in practice Core's calls are acknowledged and ignored. Making the two sides actually share organisations means following ADR-0014 (Clerk `org_id` claim, phase 2), a larger decision recorded in `replica/engine-plan.md`'s "who bills" section.

## 2026-10-12 ADR-0014 phase 2: Clerk organisations (branch feat/adr-0014-clerk-orgs)
A Clerk token that names an organisation now links Vigilo to it. `ClerkClaims` carries `org_id`/`org_role`/`org_name` (template shortcodes, or Clerk's session-token v2 object `o`). `GET /v1/orgs` and every route using the active organisation call `link_clerk_org`: an organisation admin's first visit creates a team organisation linked to the Clerk one (the admin becomes owner); later visitors are added as admin (`org:admin`) or member; an owner is never changed by a token; a non-admin on an organisation nobody has set up gets 409 (and an empty list) until an admin opens Vigilo. An explicit `X-Org-Id` still wins. Migration 0018 `core_org_plans` remembers the plan Core sends, so a plan sent before anyone opened Vigilo applies on the first link (before, it was acknowledged and lost). 829 Python tests pass, ruff clean.
**Not done (still true):** removing someone in Clerk does not remove their Vigilo membership (their token just stops naming the organisation; `X-Org-Id` access remains until a Vigilo admin removes them); Vigilo's own member, invite and billing UI still exists beside Console's; phase 3 (usage events to Core) is untouched. **Needs you:** in the Clerk dashboard add `org_id`, `org_role` and `org_name` to the `vigilo-api` JWT template (`{{org.id}}`, `{{org.role}}`, `{{org.name}}`), or none of this triggers. **Deploy:** run migration 0018, then `deploy.sh vigilo api web scanner`.

## 2026-10-13 members removed in Clerk lose access here (branch feat/clerk-member-sync)
Closes the gap left by ADR-0014 phase 2. `python -m vigilo_api.clerk_member_sync` (hourly cron, run inside the API container because the scanner has no network) lists each Clerk-linked organisation's members from Clerk's Backend API and removes the Vigilo members whose Clerk user is not in it, with an audit event `member_removed_by_clerk`. Fail-safe by design: an organisation whose list cannot be read, is empty, or no longer exists in Clerk is skipped; owners are never removed; organisations not linked to Clerk are untouched. **Consequence to know:** a linked organisation's membership now follows Clerk, so a member added only by a Vigilo invite (not in Clerk) is removed at the next run. Latency is up to an hour (Clerk webhooks would make it instant but need a signing secret and a public endpoint). 835 Python tests pass (6 new).
Deploy: `./scripts/install-member-sync-cron.sh` on the server after the deploy; dry run with `--dry-run`; first run by hand: `docker compose exec -T api uv run python -m vigilo_api.clerk_member_sync`. Rollback: remove the cron line.

## 2026-10-20 to 22 production billing, found by testing the live checkout
Checks run against production through the Chrome extension, nothing paid. **Findings and fixes:**
- **Both apps' Stripe key had expired** (`api_key_expired` in NEXORA Core's log; Vigilo got a 401). Both env files held the same key. Replaced with `scripts/rotate-stripe-key.sh` (hidden prompt, ssh on stdin, timestamped backups, recreates the three containers). After that Vigilo's monthly and yearly checkout return a Stripe URL. The key that was used had been pasted into a chat once: **roll it and rerun the script**.
- **Core's checkout failed on a stale customer** (`No such customer: cus_VKqYoe5…`): Core reuses the customer id of any existing subscriptions row for the organisation, and the only row was a canceled Sentinel test subscription whose customer no longer exists in Stripe. Row deleted after saving it to `~/vigilo-backups/core-subscriptions-stale-customer-20261019T102854Z.csv`. Core's Vigilo checkout now reaches Stripe's payment page.
- **The edge blocked every Next.js Server Action on `vigilo.onenexora.com`** (the shared Caddyfile imported `no_server_actions`, which answers 403 to the `Next-Action` header). Switching organisation, creating one and member actions failed in the browser. Fixed in NEXORA #64 (edge deployed).
- **Prices in use** (read from Stripe's request log): both apps use the Sep 27 "Vigilo Pro" prices, `price_1UKKeS…` monthly and `price_1UKKlh…` yearly. The Oct 9 duplicate product (made by `stripe_setup.py`, which only recognises a product carrying `metadata.vigilo=pro`) had its two prices archived (restorable from the dashboard). The script now stops with a clear message when an unmarked product named "Vigilo Pro" exists, instead of creating another.
- **Webhook:** `https://vigilo-api.onenexora.com/v1/billing/webhook` is registered and active, subscribed to `customer.subscription.created`, `.updated` and `.deleted`, which are the only events `vigilo_billing.webhooks` uses.
**Not yet done:** a real paid purchase and refund (the first attempt left no payment in Stripe), the NEXORA-organisation purchase through Core, rolling the exposed key, legal pages (still DRAFT), support mailboxes, a mail provider for invite and scan emails.
