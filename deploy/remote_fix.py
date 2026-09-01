#!/usr/bin/env python3
"""Connexion SSH au VPS et correctif production Mobility Health."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import paramiko
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

HOST = os.environ.get("MH_SSH_HOST", "srv1324425.hstgr.cloud")
USER = os.environ.get("MH_SSH_USER", "root")
PASSWORD = os.environ.get("MH_SSH_PASSWORD", "")
SCRIPT_DIR = Path(__file__).resolve().parent


def _ki_handler(password: str):
    def handler(title, instructions, prompt_list):
        del title, instructions
        return [password if prompt_list else "" for _ in prompt_list]

    return handler


def connect_paramiko(host: str, user: str, password: str) -> paramiko.SSHClient:
    errors = []

    def try_connect(**kwargs):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=30, **kwargs)
        return client

    for label, kwargs in (
        ("mot de passe", {"allow_agent": False, "look_for_keys": False}),
        ("clé SSH locale", {"allow_agent": True, "look_for_keys": True}),
    ):
        try:
            print(f"  Tentative auth : {label}...")
            return try_connect(**kwargs)
        except paramiko.ssh_exception.AuthenticationException as exc:
            errors.append(f"{label}: {exc}")

    print("  Tentative auth : keyboard-interactive...")
    transport = paramiko.Transport((host, 22))
    transport.connect()
    try:
        transport.auth_interactive(user, _ki_handler(password))
    except paramiko.ssh_exception.AuthenticationException as exc:
        errors.append(f"keyboard-interactive: {exc}")
        transport.close()
        msg = (
            "Authentification SSH echouee.\n"
            f"  Hote : {user}@{host}\n"
            "  Verifiez le mot de passe et l'utilisateur (root ou deployer).\n"
            "  Test manuel : ssh root@srv1324425.hstgr.cloud\n"
            "  Details :\n    - " + "\n    - ".join(errors)
        )
        raise paramiko.ssh_exception.AuthenticationException(msg) from exc

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client._transport = transport
    return client


def run_via_plink(host: str, user: str, password: str, remote_cmd: str) -> int:
    plink = shutil.which("plink")
    if not plink:
        return -1

    print("  Repli via PuTTY plink...")
    target = f"{user}@{host}"
    proc = subprocess.run(
        [plink, "-batch", "-ssh", target, "-pw", password, remote_cmd],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode


def main() -> int:
    if not PASSWORD:
        print("Definissez MH_SSH_PASSWORD avant d'executer ce script.", file=sys.stderr)
        return 1

    fix_sh = (SCRIPT_DIR / "fix-server-production.sh").read_text(encoding="utf-8")
    nginx_conf = (SCRIPT_DIR / "nginx" / "mobility-health-production.conf").read_text(encoding="utf-8")

    remote_cmd = f"""
set -e
TMP=$(mktemp -d)
mkdir -p "$TMP/nginx"
cat > "$TMP/fix-server-production.sh" << 'EOFSCRIPT'
{fix_sh}
EOFSCRIPT
cat > "$TMP/nginx/mobility-health-production.conf" << 'EOFNGINX'
{nginx_conf}
EOFNGINX
chmod +x "$TMP/fix-server-production.sh"
cd "$TMP" && bash fix-server-production.sh
"""

    print(f"Connexion a {USER}@{HOST}...")
    try:
        client = connect_paramiko(HOST, USER, PASSWORD)
    except paramiko.ssh_exception.AuthenticationException:
        code = run_via_plink(HOST, USER, PASSWORD, remote_cmd)
        if code >= 0:
            return code
        raise

    stdin, stdout, stderr = client.exec_command(remote_cmd, get_pty=True, timeout=900)
    for line in iter(stdout.readline, ""):
        print(line, end="")

    err = stderr.read().decode()
    if err.strip():
        print(err, file=sys.stderr)

    code = stdout.channel.recv_exit_status()
    client.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
