#!/usr/bin/env bash
# Run on YOUR machine (not on the server), after creating a new live key in Stripe
# (Developers -> API keys). It asks for the key with hidden input, writes it to both
# servers' env files (keeping a timestamped backup of each), recreates the three
# containers that use it, and prints the masked result. The key is sent over ssh on stdin
# and never appears in a command line, a log or this repository.
#
# Safety: both env files are checked before either is touched, each is replaced atomically
# (a temp file beside it, same owner and mode, then a rename), a failure on the second one
# restores the first, and the key's temp file on the server is unique, private and removed
# on every exit path.
#
#   ./scripts/rotate-stripe-key.sh [user@host] [path-to-ssh-key]
set -euo pipefail

host="${1:-opc@92.5.69.99}"
pem="${2:-$HOME/.ssh/nexora-prod.pem}"
ssh_cmd=(ssh -i "$pem" -o BatchMode=yes "$host")
remote_key=""

cleanup() {
  if [[ -n "$remote_key" ]]; then
    "${ssh_cmd[@]}" "rm -f -- '$remote_key'" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

read -r -s -p "Paste the new LIVE Stripe secret key (input hidden): " key
echo
if [[ ! "$key" =~ ^(sk|rk)_live_[A-Za-z0-9_]{20,}$ ]]; then
  echo "That does not look like a live Stripe key (sk_live_... or rk_live_...). Nothing changed." >&2
  exit 1
fi

# 1. The key goes to a private, uniquely named file created by mktemp (mode 0600, never
#    reused); its path comes back so it can be read once and removed on every exit path.
remote_key="$(printf '%s' "$key" | "${ssh_cmd[@]}" 'f="$(mktemp /tmp/.stripe_key.XXXXXXXX)" && cat > "$f" && printf "%s" "$f"')"
unset key
if [[ ! "$remote_key" =~ ^/tmp/\.stripe_key\.[A-Za-z0-9]+$ ]]; then
  echo "Could not create a private temp file on the server. Nothing changed." >&2
  remote_key=""
  exit 1
fi

# 2. Validate both env files first, then replace each atomically; restore on any failure.
"${ssh_cmd[@]}" "sudo python3 - '$remote_key'" <<'PY'
import os, re, shutil, sys, tempfile, time

key_file = sys.argv[1]
new = open(key_file).read().strip()
os.remove(key_file)  # read once; the local trap would also remove it
paths = ("/opt/vigilo/.env", "/opt/nexora/infrastructure/docker/.env.prod")
pattern = re.compile(r"(?m)^STRIPE_SECRET_KEY=.*$")

texts = {}
for path in paths:  # validate everything before changing anything
    text = open(path).read()
    if len(pattern.findall(text)) != 1:
        raise SystemExit(f"{path}: expected exactly one STRIPE_SECRET_KEY line, nothing changed")
    texts[path] = text

stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
done = []
try:
    for path in paths:
        backup = f"{path}.bak-pre-stripe-key-{stamp}"
        shutil.copy2(path, backup)
        updated = pattern.sub(lambda _: "STRIPE_SECRET_KEY=" + new, texts[path])
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".env.tmp.")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(updated)
                handle.flush()
                os.fsync(handle.fileno())
            shutil.copystat(path, tmp)
            st = os.stat(path)
            os.chown(tmp, st.st_uid, st.st_gid)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        done.append((path, backup))
        line = [l for l in updated.splitlines() if l.startswith("STRIPE_SECRET_KEY=")][0]
        print(f"{path}: now {line[:25]}...{line[-6:]}")
except BaseException:
    for path, backup in done:  # a later file failed: put the earlier ones back
        shutil.copy2(backup, path)
        print(f"{path}: restored from {backup}", file=sys.stderr)
    raise
PY
remote_key=""  # the python step removed it

# 3. Recreate the services that read the key so they pick it up.
"${ssh_cmd[@]}" '
  cd /opt/nexora/infrastructure/docker &&
    sudo docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate --no-deps console api &&
  cd /opt/vigilo &&
    sudo env GIT_SHA="$(git rev-parse --short HEAD)" docker compose up -d --force-recreate --no-deps api'
echo "Done. Tell Claude 'go' to run the checkout test."
