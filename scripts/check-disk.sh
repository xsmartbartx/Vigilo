#!/usr/bin/env bash
# Exit non-zero when the root filesystem is at or above a threshold (default 85%).
#   ./scripts/check-disk.sh [threshold-percent]
# Builds add 1-4 GB each and backups live on the same disk, so this is the early warning.
set -euo pipefail
threshold="${1:-85}"
used="$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')"
stamp="$(date -u +%FT%TZ)"
if [[ "$used" -ge "$threshold" ]]; then
  echo "$stamp DISK HIGH: / is at ${used}% (threshold ${threshold}%)"
  exit 1
fi
echo "$stamp ok: / is at ${used}% (threshold ${threshold}%)"
