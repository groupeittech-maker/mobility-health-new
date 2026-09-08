#!/usr/bin/env bash
# Prépare ~/.ssh pour mhc-vps depuis les secrets GitHub Actions.
set -euo pipefail

for name in SSH_HOST SSH_USER SSH_PRIVATE_KEY; do
  if [ -z "${!name:-}" ]; then
    echo "::error::Secret $name non configuré"
    exit 1
  fi
done

mkdir -p ~/.ssh && chmod 700 ~/.ssh
HOST="$(echo "$SSH_HOST" | tr -d '[:space:]')"
PORT="$(echo "${SSH_PORT:-22}" | tr -d '[:space:]')"
if [[ "$HOST" == *@* ]]; then
  echo "::error::SSH_HOST doit être un hostname seul, sans user@"
  exit 1
fi

python3 << 'PY'
import os, sys
raw = os.environ.get("SSH_PRIVATE_KEY") or ""
if not raw.strip():
    print("::error::SSH_PRIVATE_KEY vide")
    sys.exit(1)
key = raw.replace("\r\n", "\n").replace("\r", "\n")
if "BEGIN" in key and "\\n" in key:
    key = key.replace("\\n", "\n")
key = key.strip() + "\n"
path = os.path.expanduser("~/.ssh/id_ed25519")
with open(path, "w", newline="\n") as f:
    f.write(key)
os.chmod(path, 0o600)
PY

ssh-keygen -y -f ~/.ssh/id_ed25519 >/dev/null
ssh-keyscan -4 -p "$PORT" -H "$HOST" >> ~/.ssh/known_hosts 2>/dev/null || true
chmod 600 ~/.ssh/known_hosts || true
{
  echo "Host mhc-vps"
  echo "  HostName ${HOST}"
  echo "  User ${SSH_USER}"
  echo "  Port ${PORT}"
  echo "  IdentityFile ~/.ssh/id_ed25519"
  echo "  AddressFamily inet"
  echo "  BatchMode yes"
  echo "  StrictHostKeyChecking accept-new"
  echo "  ConnectTimeout 25"
  echo "  ServerAliveInterval 30"
  echo "  ServerAliveCountMax 3"
} >> ~/.ssh/config
chmod 600 ~/.ssh/config

echo "Cible : ${SSH_USER}@${HOST}:${PORT}"
bash .github/scripts/ssh-connectivity-check.sh "$HOST" "$PORT" "${SSH_CONNECT_ATTEMPTS:-8}" "${SSH_CONNECT_WAIT:-20}"

for attempt in 1 2 3 4 5; do
  echo "SSH test (tentative ${attempt}/5)…"
  if ssh -4 mhc-vps "echo OK; hostname; date"; then
    exit 0
  fi
  [ "$attempt" -lt 5 ] && sleep 15
done

echo "::error::SSH Connection timed out"
exit 1
