#!/usr/bin/env bash
# Run ON THE SERVER, from the repo checkout, as the user that runs Docker (opc):
#   ./scripts/install-backup-cron.sh [--dry-run] [backup-dir] [days-to-keep]
# Installs two cron lines (safe to re-run; it replaces its own lines and keeps the rest):
#   03:00 daily  scripts/backup.sh into backup-dir, deleting archives older than days-to-keep
#   03:30 daily  scripts/check-disk.sh, appending a line to backup-dir/disk.log
# Backups live on the same disk as the data: copy them off the machine as well.
set -euo pipefail
cd "$(dirname "$0")/.."

dry=0; [[ "${1:-}" == "--dry-run" ]] && { dry=1; shift; }
repo="$(pwd)"; out="${1:-$HOME/vigilo-backups}"; keep="${2:-14}"
case "$keep" in
  ''|*[!0-9]*) echo "days-to-keep must be a number" >&2; exit 2 ;;
  *) ;;
esac

tag="# vigilo (managed by scripts/install-backup-cron.sh)"
path="PATH=/usr/local/bin:/usr/bin:/bin"
backup="0 3 * * * cd \"$repo\" && ./scripts/backup.sh \"$out\" >> \"$out/backup.log\" 2>&1 && find \"$out\" -name 'vigilo-backup-*.tar.gz' -mtime +$keep -delete"
disk="30 3 * * * cd \"$repo\" && ./scripts/check-disk.sh 85 >> \"$out/disk.log\" 2>&1"

if [[ "$dry" == 1 ]]; then
  printf 'would install:\n%s\n%s\n%s\n%s\n' "$tag" "$path" "$backup" "$disk"; exit 0
fi

mkdir -p "$out"
kept="$(crontab -l 2>/dev/null | grep -v -F "managed by scripts/install-backup-cron.sh" \
  | grep -v -F "scripts/backup.sh" | grep -v -F "scripts/check-disk.sh" | grep -v -x "$path" || true)"
{ [[ -n "$kept" ]] && printf '%s\n' "$kept"; printf '%s\n%s\n%s\n%s\n' "$tag" "$path" "$backup" "$disk"; } | crontab -
echo "installed:"; crontab -l | tail -4
