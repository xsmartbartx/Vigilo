#!/usr/bin/env bash
# Run on YOUR machine, after creating a Postmark Server and verifying the sending domain
# (a DKIM record and a Return-Path record in DNS). It asks for the Server API token with hidden
# input, stores POSTMARK_SERVER_TOKEN and MAIL_FROM_ADDRESS in /opt/vigilo/.env (backup first,
# atomic replace, original owner and mode kept), recreates the two services that send email
# (api: invitations; scanner: alert notifications) and sends one real test message so the whole
# path is proven. The token travels over ssh on stdin: never on a command line, in a log or here.
#
#   ./scripts/setup-postmark.sh [user@host] [path-to-ssh-key] [test-recipient]
set -euo pipefail

host="${1:-opc@92.5.69.99}"
pem="${2:-$HOME/.ssh/nexora-prod.pem}"
recipient="${3:-support@onenexora.com}"
ssh_cmd=(ssh -i "$pem" -o BatchMode=yes "$host")
remote_key=""

cleanup() {
  [[ -n "$remote_key" ]] && "${ssh_cmd[@]}" "rm -f -- '$remote_key'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

read -r -s -p "Paste the Postmark Server API token (input hidden): " token
echo
if [[ ! "$token" =~ ^[A-Za-z0-9-]{20,}$ ]]; then
  echo "That does not look like a Postmark server token. Nothing changed." >&2
  exit 1
fi
read -r -p "Send emails from [scans@onenexora.com]: " from
from="${from:-scans@onenexora.com}"
if [[ ! "$from" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
  echo "That is not an email address. Nothing changed." >&2
  exit 1
fi

# 1. The token goes to a private, uniquely named file (mktemp, mode 0600), removed on every exit.
remote_key="$(printf '%s' "$token" | "${ssh_cmd[@]}" 'f="$(mktemp /tmp/.postmark_token.XXXXXXXX)" || exit 1; if cat > "$f"; then printf "%s" "$f"; else rm -f -- "$f"; exit 1; fi')"
unset token
if [[ ! "$remote_key" =~ ^/tmp/\.postmark_token\.[A-Za-z0-9]+$ ]]; then
  echo "Could not create a private temp file on the server. Nothing changed." >&2
  remote_key=""
  exit 1
fi

# 2. Set both variables atomically (replace the line if present, append if not).
"${ssh_cmd[@]}" "sudo python3 - '$remote_key' '$from'" <<'PY'
import os, re, shutil, sys, tempfile, time

key_file, sender = sys.argv[1], sys.argv[2]
token = open(key_file).read().strip()
os.remove(key_file)
path = "/opt/vigilo/.env"
text = open(path).read()


def set_var(body: str, name: str, value: str) -> str:
    line = f"{name}={value}"
    pattern = re.compile(rf"(?m)^{name}=.*$")
    if pattern.search(body):
        return pattern.sub(lambda _: line, body, count=1)
    return body + ("" if body.endswith("\n") else "\n") + line + "\n"


updated = set_var(set_var(text, "POSTMARK_SERVER_TOKEN", token), "MAIL_FROM_ADDRESS", sender)
backup = f"{path}.bak-pre-postmark-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
shutil.copy2(path, backup)
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
print(f"{path}: POSTMARK_SERVER_TOKEN set (ends ...{token[-4:]}), MAIL_FROM_ADDRESS={sender}")
PY
remote_key=""

# 3. Recreate the services that send email.
"${ssh_cmd[@]}" '
  cd /opt/vigilo &&
  sudo env GIT_SHA="$(git rev-parse --short HEAD)" docker compose up -d --force-recreate --no-deps api scanner'
echo "Waiting for the API to come up..."
healthy=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 5 -o /dev/null https://vigilo-api.onenexora.com/healthz; then
    healthy=1
    break
  fi
  sleep 3
done
if [[ "$healthy" != 1 ]]; then
  echo "The API did not become healthy after the restart. The token is saved; check the api container's logs." >&2
  exit 1
fi

# 4. One real message through Vigilo's own sender, so token, sender address and domain are proven.
echo "Sending a test email to $recipient ..."
"${ssh_cmd[@]}" "sudo docker exec -i vigilo-self-host-api-1 uv run python - '$recipient'" <<'PY'
import asyncio, sys
from vigilo_integrations.mail import send_transactional_email

to = sys.argv[1]
asyncio.run(
    send_transactional_email(
        to,
        "Vigilo email test",
        "<p>This is a test message from Vigilo's production server. Postmark is working.</p>",
        "This is a test message from Vigilo's production server. Postmark is working.",
    )
)
print("Postmark accepted the message for", to)
PY
echo "Done. Check the inbox of $recipient, then tell Claude."
