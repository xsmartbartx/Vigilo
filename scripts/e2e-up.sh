#!/usr/bin/env bash
# Start the backend the browser tests need, on a fresh database: Postgres schema
# vigilo_e2e, the API on :8000 (CORS for http://localhost:3000) and a scanner
# worker. Leaves them running in the background; stop them with scripts/e2e-down.sh.
# The web app is started by Playwright itself. Needs docker compose's Postgres and
# Redis up, and a repo-root .env (copy .env.example).
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/e2e-down.sh
./scripts/e2e-reset-db.sh
export DATABASE_URL="postgresql://vigilo:${POSTGRES_PASSWORD:-vigilo-dev-secret}@localhost:5433/vigilo_e2e"
export WEB_APP_URL="http://localhost:3000"
# The browser tests must never reach a real payment provider, whatever .env holds:
# blank every Stripe setting for the processes started here (the process
# environment wins over --env-file). The specs expect the "not configured" error.
export STRIPE_SECRET_KEY="" STRIPE_WEBHOOK_SECRET="" STRIPE_PRICE_ID_PRO="" \
  STRIPE_PRICE_ID_PRO_YEARLY="" STRIPE_PORTAL_CONFIGURATION_ID=""
# The anonymous-scan throttle keeps hourly counters in Redis; repeated browser runs from one
# address and email would trip it, so it is off for the test stack (the API tests cover it).
export SCAN_RATE_PER_IP_PER_HOUR=0 SCAN_RATE_PER_EMAIL_PER_HOUR=0
mkdir -p .e2e-logs
nohup uv run --env-file .env uvicorn vigilo_api.main:app --port 8000 > .e2e-logs/api.log 2>&1 &
nohup uv run --env-file .env arq vigilo_scanner.worker.WorkerSettings > .e2e-logs/worker.log 2>&1 &
for _ in $(seq 1 30); do
  curl -fs http://localhost:8000/healthz >/dev/null 2>&1 && { echo "api up; logs in .e2e-logs/"; exit 0; }
  sleep 1
done
echo "api did not start; see .e2e-logs/api.log" >&2
exit 1
