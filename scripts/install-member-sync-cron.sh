#!/usr/bin/env bash
# Run ON THE SERVER, from the repo checkout, as the user that runs Docker (opc):
#   ./scripts/install-member-sync-cron.sh [--dry-run]
# Installs one hourly cron line that removes members who were removed from their Clerk
# organisation (ADR-0014). Safe to re-run; it replaces its own line and keeps the rest.
set -euo pipefail
cd "$(dirname "$0")/.."

dry=0; [[ "${1:-}" == "--dry-run" ]] && dry=1
repo="$(pwd)"; log="$HOME/vigilo-backups/member-sync.log"
tag="# vigilo member sync (managed by scripts/install-member-sync-cron.sh)"
path="PATH=/usr/local/bin:/usr/bin:/bin"
line="17 * * * * cd \"$repo\" && docker compose exec -T api uv run python -m vigilo_api.clerk_member_sync >> \"$log\" 2>&1"

if [[ "$dry" == 1 ]]; then printf 'would install:\n%s\n%s\n%s\n' "$tag" "$path" "$line"; exit 0; fi

mkdir -p "$(dirname "$log")"
kept="$(crontab -l 2>/dev/null | grep -v -F "install-member-sync-cron.sh" \
  | grep -v -F "vigilo_api.clerk_member_sync" | grep -v -x "$path" || true)"
{ [[ -n "$kept" ]] && printf '%s\n' "$kept"; printf '%s\n%s\n%s\n' "$tag" "$path" "$line"; } | crontab -
echo "installed:"; crontab -l | tail -4
