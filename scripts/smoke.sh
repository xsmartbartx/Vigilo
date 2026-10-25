#!/usr/bin/env bash
# Post-deploy smoke check: read-only GETs against the live URLs, no credentials.
#   ./scripts/smoke.sh https://vigilo.onenexora.com https://vigilo-api.onenexora.com
# Exits non-zero if any check fails.
set -uo pipefail

WEB="${1:?usage: smoke.sh <web-url> <api-url>}"
API="${2:?usage: smoke.sh <web-url> <api-url>}"
WEB="${WEB%/}"; API="${API%/}"
fail=0

check() { # name url expected-status [body-substring]
  local name="$1" url="$2" want="$3" needle="${4:-}" out code
  out=$(curl -sS -m 15 -w $'\n%{http_code}' "$url" 2>&1) || { echo "FAIL  $name: no response ($url)"; fail=1; return; }
  code="${out##*$'\n'}"
  if [ "$code" != "$want" ]; then echo "FAIL  $name: got $code, want $want ($url)"; fail=1; return; fi
  if [ -n "$needle" ] && ! printf '%s' "$out" | grep -q -- "$needle"; then
    echo "FAIL  $name: body lacks '$needle' ($url)"; fail=1; return
  fi
  echo "ok    $name"
}

commit="$(curl -s -m 10 "$API/version" | sed -n 's/.*"commit":"\([^"]*\)".*/\1/p')"
echo "      deployed commit: ${commit:-not reported (older build)}"
check "api health"            "$API/healthz"                       200 ok
check "web home"              "$WEB/"                              200
check "web pricing"           "$WEB/pricing"                       200
check "trust page"            "$WEB/trust"                         200 "Trust and security"
check "security.txt"          "$WEB/.well-known/security.txt"      200 "Contact: mailto:"
check "acceptable use (scanner User-Agent URL)" "$WEB/aup"         200
check "sign-in page"          "$WEB/sign-in"                       200
check "console needs sign-in" "$API/v1/orgs"                       401

# Certificates: at least 14 days left on both hosts.
for host in "${WEB#https://}" "${API#https://}"; do
  if echo | openssl s_client -connect "$host:443" -servername "$host" 2>/dev/null \
      | openssl x509 -noout -checkend $((14*86400)) >/dev/null 2>&1; then
    echo "ok    certificate $host"
  else
    echo "FAIL  certificate $host: missing or expires within 14 days"; fail=1
  fi
done

[ "$fail" = 0 ] && echo "all checks passed" || echo "SOME CHECKS FAILED"
exit "$fail"
