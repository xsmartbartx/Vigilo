#!/usr/bin/env bash
# Run on YOUR machine (not on the server), after creating a new live key in Stripe
# (Developers -> API keys). It asks for the key with hidden input, writes it to both
# servers' env files (keeping a timestamped backup of each), recreates the three
# containers that use it, and prints the masked result. The key is sent over ssh on stdin
# and never appears in a command line, a log or this repository.
#
#   ./scripts/rotate-stripe-key.sh [user@host] [path-to-ssh-key]
set -euo pipefail

host="${1:-opc@92.5.69.99}"
pem="${2:-$HOME/.ssh/nexora-prod.pem}"
ssh_cmd=(ssh -i "$pem" -o BatchMode=yes "$host")

read -r -s -p "Paste the new LIVE Stripe secret key (input hidden): " key
echo
if [[ ! "$key" =~ ^(sk|rk)_live_[A-Za-z0-9_]{20,}$ ]]; then
  echo "That does not look like a live Stripe key (sk_live_... or rk_live_...). Nothing changed." >&2
  exit 1
fi

# 1. The key goes to a private temp file on the server, read once and deleted below.
printf '%s' "$key" | "${ssh_cmd[@]}" 'umask 077; cat > /tmp/.stripe_key_new'
unset key

# 2. Replace the STRIPE_SECRET_KEY line in both env files, backing each up first.
"${ssh_cmd[@]}" 'sudo python3 -' <<'PY'
import os, re, shutil, time

new = open("/tmp/.stripe_key_new").read().strip()
os.remove("/tmp/.stripe_key_new")
stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
for path in ("/opt/vigilo/.env", "/opt/nexora/infrastructure/docker/.env.prod"):
    text = open(path).read()
    if not re.search(r"(?m)^STRIPE_SECRET_KEY=", text):
        raise SystemExit(f"{path}: no STRIPE_SECRET_KEY line, nothing changed")
    shutil.copy2(path, f"{path}.bak-pre-stripe-key-{stamp}")
    open(path, "w").write(re.sub(r"(?m)^STRIPE_SECRET_KEY=.*$", lambda _: "STRIPE_SECRET_KEY=" + new, text))
    line = [l for l in open(path).read().splitlines() if l.startswith("STRIPE_SECRET_KEY=")][0]
    print(f"{path}: now {line[:25]}...{line[-6:]}")
PY

# 3. Recreate the services that read the key so they pick it up.
"${ssh_cmd[@]}" '
  cd /opt/nexora/infrastructure/docker &&
    sudo docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate --no-deps console api &&
  cd /opt/vigilo &&
    sudo env GIT_SHA="$(git rev-parse --short HEAD)" docker compose up -d --force-recreate --no-deps api'
echo "Done. Tell Claude 'go' to run the checkout test."
