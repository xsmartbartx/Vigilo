# Deploy (preflight run 2026-10-08, updated 2026-10-09 after the no-keys fixes)

**Verdict: do not deploy yet.** Nothing was published, bought, signed in to or changed in production. Four checks fail and several things only you can do are open.

## 1. Preflight results

| check | result | detail |
| --- | --- | --- |
| Browser tests (`npx playwright test`) | **pass: 93 passed, 15 skipped on purpose** (rerun 2026-10-10 on the merged tree, 0 failed; run under `caffeinate -d -i -s` on macOS, see build-log) (desktop and mobile; real Clerk dev instance; real API, scanner worker and Postgres; axe on every page) | Covers public pages, sign-in, console, dashboard, members and invites, role change and removal (a second member added directly to the test database, never at Clerk), organisation switching and per-org isolation, the launcher's Enable, org creation, targets, API-key and checkout error handling, audit log, account-deletion form validation, and a real scan to a finished report with accept-risk and restore. **Not covered:** accepting an invitation as a second person, billing against real Stripe, invitation email, PDF export in the browser suite, share links and monitoring (need a Pro plan), and a real account deletion (never run against a real person's account). |
| Parity (`parity.py`) | **pass, with a caveat** | 95.9 / 100, 13 of 13 must-haves (rule: all must-haves, 80+). The jump from 77.3 comes from rescoping to the one product that exists (the other four engines are separate projects, now marked "Coming soon" and not enableable), not from new features; see `parity.md`. |
| Rebrand sweep | pass (rerun 2026-10-09) | clean for the competitor names in `brand.json`. Does not cover the unresolved vigilo.io / Nexora questions below. |
| Store listing (`listing.py`) | n/a | no mobile app. |
| Production build (`npm run build`) | pass | compiles with placeholder Clerk env; real keys not tried. |
| Python tests | **pass: 784 passed, 0 failed** | Run locally against a moto S3 server (the 4 object-storage tests included). MinIO images can no longer be pulled (bitnami removed, quay 401), so CI and tests use `moto_server`. The workflow itself has **not yet run on GitHub**. |
| Open S1/S2 bugs | none known | but the console, report, invite, billing and audit screens have never been rendered, so "none known" is weak. |
| `npm audit --omit=dev` | pass, 0 vulnerabilities (rerun 2026-10-09; was a real finding) | the first read found a **critical Next.js remote-code-execution advisory in `next/og`** (16.2.0 to 16.3.5): upgraded to 16.4.0, plus `sharp` and `source-map-js`. Production audit is clean; dev-only findings remain (e.g. `braces`). Python dependencies not audited. |
| Secrets in git | pass | a live Stripe key was found once in the uncommitted `.env.example`, removed before any commit; only `.env.example` and `.env.production.example` are tracked; `.env` and `.env.*` are ignored. |
| Privacy / terms / cookies / AUP pages | exist | privacy now names invitation emails; have a lawyer or yourself review the text. No cookie banner exists: fine only if you set no non-essential cookies (Clerk's are essential; add no analytics without one). |
| Account deletion works | **built, 10 tests, not exercised in a browser or against a real Clerk** | `/console/account`, `POST /v1/me/delete`. Blocks while an owned org has other members or a renewing paid plan; deletes owned orgs and their data, stored files and the Clerk user; the audit log outlives the account (migration 0016). No ownership transfer exists yet. |
| Favicon, title, OG image are yours | **placeholder** | a drawn placeholder icon, apple icon and 1200x630 social images (platform and Vigilo) replace the framework default; titles set per page. They are placeholders from the brief, not a logo; replace after the name is cleared. |

## 2. Blockers, in order

1. **Domain and name.** Addresses and the scanner User-Agent now use `onenexora.com` (see `dns.md`); the Nexora trademark question remains. Earlier note: `vigilo.io` was registered 2024-06-14 and serves a live site; I cannot tell who owns it. `brand.config.json`, `SECURITY.md`, `docker-compose.self-host.yml` and `.env.example` send support@/abuse@/security@ mail, the scanner User-Agent URL and the DNS-verification key there. Confirm you own it or move them. `onenexora.com` is registered to you (2026-09-20). A same-category product named Nexora exists (see `brand.md`); get a trademark search before spending on the brand.
2. **Keys only you can create** (I never enter them): Clerk production instance, Stripe live keys and webhook secret, Postmark server token and a verified sending domain, optional Anthropic key.
3. ~~Run the browser tests~~ done: 93 passed, 15 skipped.
4. ~~Account deletion~~ built, and ownership transfer now exists so a team owner can leave; still needs one real run with Clerk production keys.
5. **Brand assets**: replace the placeholder icon and social images with the real logo (`brand.md` has the brief).
6. ~~Must-have gap~~ closed by rescoping to Vigilo (13 of 13). Original note: the remaining must-haves are mostly "partial" rows that need real rendering/verification, not new code. Parity is not a reason to block if you decide the scope is right; then change the scope in `features.csv` instead of ignoring the rule.
7. **CI must be green on GitHub.** The workflow now starts moto for the Python job and has an `e2e` job (Postgres, Redis, moto, API, worker, Playwright). Dry-run locally with only the workflow's environment: 91 passed, 15 skipped. To enable the `e2e` job add three repository secrets: `E2E_CLERK_PUBLISHABLE_KEY`, `E2E_CLERK_SECRET_KEY`, `E2E_USER_EMAIL` (use a dedicated throwaway Clerk dev user and dev instance, never production). Without them the job passes with a warning and skips the suite.
8. ~~Stale docs~~ `docs/self-hosting.md` and the billing/organisation part of `docs/api.md` corrected (Stripe, Free and Pro, per-organisation billing, deletion, error tracking).

## 3. How this repo deploys (not Vercel)

The repo ships a **Docker Compose + Caddy deployment for a single VPS** (`docker-compose.self-host.yml`, `Caddyfile`, `scripts/deploy.sh`, `scripts/backup.sh`). The scanner needs an isolated network zone and Playwright for PDFs, which is why it is not a serverless deploy. Use that path unless you decide otherwise.

What you do (accounts and money are yours):
1. Buy/choose the domain(s); get a VPS (Docker + Compose v2, ports 80/443 open).
2. DNS at your registrar: `A  <WEB_DOMAIN>  -> <VPS IP>`, `A  <API_DOMAIN>  -> <VPS IP>` (e.g. `app.` and `api.` under your domain). Caddy then issues HTTPS certificates by itself. Pick one canonical web host and redirect the other.
3. Clerk: create a **production** instance for the domain. Clerk shows the exact DNS records it needs (a frontend-API CNAME, an accounts CNAME and email DKIM CNAMEs): add them as shown. Create the JWT template with an `email` claim named as `NEXT_PUBLIC_CLERK_JWT_TEMPLATE`. Set the allowed origins/redirects to the production domain.
4. Stripe: switch to live mode, create the Vigilo Pro monthly and yearly prices, add a webhook endpoint `https://<API_DOMAIN>/v1/billing/webhook` for `customer.subscription.created`, `.updated`, `.deleted`, copy its signing secret, configure the customer portal. Make **one real purchase and refund it**. You can do the object setup with `uv run python scripts/stripe_setup.py --mode live --apply --webhook-url https://<API_DOMAIN>/v1/billing/webhook` (dry run first; key from your shell environment only).
5. Postmark: verify the sending domain; add the SPF (TXT) and DKIM records it displays and the Return-Path CNAME; add DMARC `_dmarc  TXT  v=DMARC1; p=none; rua=mailto:<you>@<domain>` and tighten to `quarantine` once reports are clean. Use a sender like `invites@<domain>` (the default `scans@vigilo.io` is not yours to assume).
6. On the VPS: `cp .env.example .env`, fill every value below, then
   `docker compose -f docker-compose.self-host.yml up -d --build` and
   `docker compose -f docker-compose.self-host.yml exec api uv run alembic -c packages/persistence/alembic.ini upgrade head` (later releases: `scripts/deploy.sh`).

Production env (names only; values are yours; `SENTRY_DSN` optional): `WEB_DOMAIN`, `API_DOMAIN`, `WEB_APP_URL=https://<WEB_DOMAIN>`, `PUBLIC_API_BASE_URL=https://<API_DOMAIN>`, `POSTGRES_PASSWORD`, `OBJECT_STORE_SECRET_KEY` (both: non-default), `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_CLERK_JWT_TEMPLATE`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_PRO_YEARLY`, `STRIPE_PORTAL_CONFIGURATION_ID`, `POSTMARK_SERVER_TOKEN`, `MAIL_FROM_ADDRESS`, optional `ANTHROPIC_API_KEY`. `NEXT_PUBLIC_*` values are baked into the web image at build time: change them only by rebuilding.

Gaps in the production set-up:
- **Database**: the compose Postgres is on the same VPS. Backups: `scripts/backup.sh` (Postgres + MinIO evidence to a tarball). Schedule it and **copy the tarballs off the machine**; test one restore.
- **Migrations**: run by `scripts/deploy.sh`, not by hand, once you adopt it.
- **Error tracking**: the API and scanner now have an optional Sentry hook, off until you set `SENTRY_DSN` (no personal data, request bodies, headers, cookies, query strings or one-time link tokens are sent). The web app has none. **Still missing:** an external uptime check on `/` and `https://<API_DOMAIN>/healthz`, an alert to your email or phone, and analytics (if you add any, add a cookie notice).
- **No staging environment** and no preview deploys on this path.

## 4. First week, once live
Watch: webhook deliveries in Stripe (any 4xx/5xx), bounced or spam-foldered invite and scan emails, scan failures and the scanner queue, Postgres disk and backup age, certificate renewal, the audit log for unexpected actions, and signup-to-first-scan.
Do the core flow yourself on the live site (visit, scan, sign up, create an org, invite a second address, subscribe with a real card and refund, cancel in the portal) and then on your phone.

## 5. Where this stands now
Options A and B are done and parity passes (scoped to Vigilo). Still failing the preflight: `vigilo.io` ownership, the Nexora trademark question, a first green CI run on GitHub, and an uptime check. Still only you: Clerk production, Stripe live and Postmark keys, the domain, the VPS.
- **C.** Change the target (e.g. a smaller launch scope) and re-score parity honestly.
Nothing deploys until the preflight passes and you say go.

## Security note, 2026-10-09
A live Stripe secret key was pasted into the chat and later written to `.env`. It was never used by me, but it must be treated as exposed: **roll it in the Stripe dashboard** (Developers, API keys, Roll key) and replace the `.env` line with a **test** key (`sk_test_...`) for development. The browser-test scripts now blank every Stripe variable so tests cannot reach a real provider whatever `.env` holds.

**Stripe live (2026-10-09):** product, both prices and the portal configuration exist in the live account (IDs in `build-log.md`). Still to do, by you: the webhook endpoint once the API domain exists (`uv run python scripts/stripe_setup.py --mode live --apply --webhook-url https://<API_DOMAIN>/v1/billing/webhook`, prints the signing secret once), the three IDs and the live key in the production host environment, and one real purchase with your own card, then refund it.

**Production env:** `.env.production.example` lists every variable for the VPS (no values). Copy it to `.env` on the server. `POSTGRES_PASSWORD` and `OBJECT_STORE_SECRET_KEY` must be set: the compose file otherwise falls back to a published dev password. `.gitignore` now un-ignores that example file; the real `.env` stays ignored.

**DNS:** proposal and exact record table in `replica/dns.md` (app. and api. under onenexora.com, mail from scans@onenexora.com). Waiting for your domain decision and the VPS IP.

**Clerk production:** step-by-step in `replica/clerk-production.md` (domain `vigilo.onenexora.com`, JWT template `vigilo-api` with an `email` claim, JWKS URL, rebuild the web image after setting the publishable key).

**Postmark:** step-by-step in `replica/postmark-setup.md` (verify onenexora.com, merge the SPF record with Google Workspace's, sender scans@, server token to the server env).

## Launch runbook (in order)

Each step names its guide. Stop at the first failure.

1. **Decide the name and domain.** Nexora trademark; `onenexora.com` as the home (`dns.md`).
2. **DNS at Squarespace**: A records `app` and `vigilo-api` to `92.5.69.99` (`dns.md`). Check with `dig +short A vigilo.onenexora.com`. *`app` resolves as of 2026-10-09; `vigilo-api` already answers but with something else (see dns.md).*
3. **Mailboxes** in Google Workspace: `support@`, `abuse@`, `security@onenexora.com` (the `scans@` sender is only needed once Postmark is on).
4. **Clerk production instance** and its DNS records (`clerk-production.md`). Verify goes green.
5. ~~**Postmark**~~ **skipped by the owner (2026-10-09).** Leave `POSTMARK_SERVER_TOKEN` empty. The app runs without it: invitation, monitoring-alert and scan-report emails are not sent and each caller handles that without an error page (invitations report `email_status` as `not_configured`; the invite link is still returned and can be shared by hand). Revisit with `postmark-setup.md` when email matters.
6. **Server**: pull the repo, copy `.env.production.example` to `.env`, fill it in. Set `COMPOSE_FILE=docker-compose.self-host.yml:docker-compose.external-proxy.yml`, strong `POSTGRES_PASSWORD` and `OBJECT_STORE_SECRET_KEY`, and the Stripe/Clerk/Postmark values.
7. **First start**: `docker compose up -d --build`, then `./scripts/deploy.sh` (runs the migrations).
8. **Existing Caddy**: add the two site blocks from `Caddyfile.external-proxy.example`, `caddy validate`, reload.
9. **Stripe webhook**: `uv run python scripts/stripe_setup.py --mode live --apply --webhook-url https://vigilo-api.onenexora.com/v1/billing/webhook` from your own shell; put the printed signing secret in the server `.env` and redeploy.
10. **Smoke check**: `./scripts/smoke.sh https://vigilo.onenexora.com https://vigilo-api.onenexora.com` must print `all checks passed`.
11. **First real run**: sign up with your own email, run a scan on a site you own, invite a second address you own and check the email arrives, then buy Pro with your own card and refund it.
12. **Watch**: schedule `scripts/backup.sh`, copy the tarballs off the machine and test one restore; add an uptime monitor on `https://vigilo.onenexora.com/` and `https://vigilo-api.onenexora.com/healthz`; set `SENTRY_DSN`.

**Server shortcut:** `scripts/vps_setup.sh` does steps 6 to 8 on the server in one go (`git clone https://github.com/N3xora/Vigilo.git && cd Vigilo && ./scripts/vps_setup.sh`). It writes `.env` from `.env.production.example`, generates the two internal passwords, asks for the Clerk and Stripe secrets with hidden input, sets external-proxy mode, refuses to run if ports 3000/8000 are taken, starts the stack, runs the migrations, and prints the Caddy blocks for your hostnames. It never overwrites an existing `.env`. Tested here only with `--no-start` and fake inputs; the Docker part has not run.

## 2026-10-10: this is an update, not a first deploy

A Vigilo deployment already runs on `92.5.69.99`: `https://vigilo.onenexora.com` serves an older build of this web app (Next.js behind Caddy, Clerk **production** key, `noindex`; `/trust`, `/pricing` and `/products/vigilo` return 404), and `vigilo-api.onenexora.com` is very likely its API (`/healthz` ok, no `/v1/orgs`). `origin/main` now contains this work (pull request #9 from `deploy-prep` was merged on 2026-10-10).

So do **not** run `scripts/vps_setup.sh` there: it refuses to overwrite `.env` and aborts on ports 3000/8000. Update the existing checkout instead:

1. `docker compose ps` and `git log -1` in the existing checkout: confirm which commit runs.
2. **Database revision (checked 2026-10-10: production is at `0009`, upstream's `0009_org_accounts`).** The migrations were renumbered to 0010-0017 behind it, so `./scripts/deploy.sh` is safe to run once that fix is merged. Original check: `docker compose exec api uv run alembic -c packages/persistence/alembic.ini current`. If it prints `0009_org_accounts` (upstream's migration, dropped in the merge), the upgrade will fail with an unknown revision; stop and see the build log.
3. `./scripts/backup.sh`, and copy the tarball off the machine.
4. `git pull` on `main`, then `./scripts/deploy.sh` (pulls, rebuilds, migrates).
5. Set the new env values if missing (`.env.production.example` lists them); the existing Clerk production keys stay.
6. `./scripts/smoke.sh https://vigilo.onenexora.com https://vigilo-api.onenexora.com`.

### Production state found on 2026-10-10
- `/opt/vigilo` runs `ebe4106` (upstream `main` before pull request #9). Database revision `0009`.
- `/opt/vigilo/.env` uses `STRIPE_PRICE_ID_PRO=price_1UKKeS...` and `STRIPE_PRICE_ID_PRO_YEARLY=price_1UKKlh...`. The product, prices and portal that `stripe_setup.py` created on 2026-10-09 (`price_1UOfNw...`, `price_1UOfNx...`) are **not** referenced there. Decide which set to keep, then archive the other in Stripe and set the env to match. Do not change the env while subscriptions exist on the old prices without checking: the webhook maps price IDs to plans.
- The server also runs the Nexora platform from `/opt/nexora` (`deploy.sh nexora console api ...`). Check it does not depend on upstream's NEXORA Core billing sync (`/v1/internal/org-plan`), which this branch removed.

### Showing the running commit (2026-10-11)
`/version` now includes `"commit"` (the image's `GIT_SHA` build arg; `"unknown"` without one) and `scripts/smoke.sh` prints it. The repo's own `scripts/deploy.sh` exports `GIT_SHA` before building. The shared platform script (`/opt/nexora/infrastructure/deployment/deploy.sh`, a different repository) is what actually deploys production and must export it too, or the field stays `"unknown"`. In its `vigilo)` branch, after `git pull --ff-only`, add:

    export GIT_SHA="$(git rev-parse --short HEAD)"

`docker compose build` then picks it up through the compose file's `GIT_SHA: ${GIT_SHA:-unknown}`.

### Automatic backups and a disk check (2026-10-11)
On the server, from the checkout (`/opt/vigilo`), as the user that runs Docker:

    ./scripts/install-backup-cron.sh --dry-run          # shows the two cron lines
    ./scripts/install-backup-cron.sh                    # installs them (re-runnable)

03:00 daily: `backup.sh` into `~/vigilo-backups`, keeping 14 days. 03:30 daily: `check-disk.sh 85`, appending a line to `disk.log` (it exits non-zero at 85% or more; nothing emails it yet, so read the log or add an alert). The backups sit on the same disk as the data, so also copy them off the machine. A restore was tested on 2026-10-11 (the 0009-era dump restored into a scratch database: 5 accounts, 5 projects, 18 tables).

### NEXORA Core plan sync (restored 2026-10-12)
`POST /v1/internal/org-plan` exists again. It is off (404) unless `NEXORA_SYNC_SECRET` is set, and the value must equal Core's. Production had it set for the Core integration: **check without printing values**, then redeploy:

    ssh -i ~/.ssh/nexora-prod.pem opc@92.5.69.99 "grep -c '^NEXORA_SYNC_SECRET=.' /opt/vigilo/.env"   # 1 = set

After the deploy an unsigned call must answer 401 (what Nexora's own smoke test expects):

    curl -s -o /dev/null -w "%{http_code}\n" -X POST https://vigilo-api.onenexora.com/v1/internal/org-plan -H 'content-type: application/json' -d '{}'

### Clerk organisations (ADR-0014 phase 2, 2026-10-12)
1. Clerk dashboard, JWT templates, `vigilo-api`: add the claims `"org_id": "{{org.id}}"`, `"org_role": "{{org.role}}"`, `"org_name": "{{org.name}}"` (they are absent when no organisation is active, which is the personal-workspace case).
2. Migrate (adds table `core_org_plans`; nothing else changes): `ssh ... "cd /opt/vigilo && sudo docker compose exec api uv run alembic -c packages/persistence/alembic.ini upgrade head"`, then deploy.
3. Rollback: remove the claims from the template and nothing links; the table is harmless.
