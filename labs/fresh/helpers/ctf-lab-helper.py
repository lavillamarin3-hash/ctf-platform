#!/usr/bin/env python3
"""Helpers root para instalación NUEVA (no sustituir los helpers históricos).

Instalar con los nombres ctf-ssh-lab, ctf-dvwa-lab y ctf-kali-session según VM.
Requisitos: Linux, Python3, useradd/chpasswd; MariaDB local para DVWA.
Ejemplo: printf '%s\n' "$FLAG" | sudo ctf-ssh-lab create a123456789ab
Toda entrada secreta llega por stdin. Salida: JSON sin claves ni flags.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import subprocess
import sys

ROOT = Path("/var/lib/cociber-fresh")
CANDIDATES = ("cociber01", "cociber02", "cociber03", "cociber04", "cociber05", "cociber06",
              "cociber07", "cociber08", "cociber09", "cociber10", "cociber11", "cociber12")


def run(command, input=None, allowed=(0,)):
    result = subprocess.run(command, input=input, text=True, capture_output=True, timeout=15, check=False)
    if result.returncode not in allowed: raise RuntimeError("Helper no completado")
    return result.stdout


def account_exists(username):
    try: return pwd.getpwnam(username)
    except KeyError: return None


def process(helper, action, run_id, data):
    username = f"ctf_{run_id}"
    marker = ROOT / f"{helper}-{run_id}.json"
    if marker.is_symlink(): raise ValueError()
    if helper == "ctf-dvwa-lab":
        # Validación estricta evita SQL/argumentos arbitrarios. run_id no es el
        # entero usado por el helper antiguo ctf-dvwa-flag.
        if action == "create":
            if not re.fullmatch(r"FLAG\{dvwa_sql_[a-f0-9]{40}\}", data): raise ValueError()
            sql = f"INSERT INTO ctf_app_db.secrets(run_id,flag) VALUES ('{run_id}','{data}') ON DUPLICATE KEY UPDATE flag=VALUES(flag);"
            run(["/usr/bin/mariadb", "--batch", "--skip-column-names"], sql)
            return {}
        if action == "destroy":
            run(["/usr/bin/mariadb", "--batch"], f"DELETE FROM ctf_app_db.secrets WHERE run_id='{run_id}';")
            return {}
        value = run(["/usr/bin/mariadb", "--batch", "--skip-column-names"], f"SELECT flag FROM ctf_app_db.secrets WHERE run_id='{run_id}';").strip()
        if not value: raise ValueError()
        return {"flag_hash": hashlib.sha256(value.encode()).hexdigest()}
    account = account_exists(username)
    if action == "destroy":
        if not marker.exists():
            if account: raise ValueError("Cuenta sin marcador de propiedad")
            return {}
        if account:
            if account.pw_uid < 1000 or account.pw_dir != f"/home/{username}": raise ValueError()
            run(["/usr/bin/pkill", "-KILL", "-u", str(account.pw_uid)], allowed=(0, 1))
            run(["/usr/sbin/userdel", "--remove", username])
        marker.unlink()
        return {}
    if action == "check":
        if not marker.exists() or not account: raise ValueError()
        if helper == "ctf-kali-session": return {"username": username}
        target = Path(account.pw_dir) / "flag.txt"
        # La flag de demostración pertenece al usuario; comprobar contenido.
        value = target.read_text().strip()
        return {"flag_hash": hashlib.sha256(value.encode()).hexdigest(), "username": username}
    if marker.exists():
        return process(helper, "check", run_id, "")
    if account: raise ValueError("No se modifica una cuenta ajena")
    if helper == "ctf-ssh-lab":
        if not re.fullmatch(r"FLAG\{ssh_[a-f0-9]{40}\}", data): raise ValueError()
        password, group = secrets.choice(CANDIDATES), "cociber-ssh"
    else:
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,100}", data): raise ValueError()
        password, group = data, "cociber-kali"
    # Persistir intención antes de useradd para recuperar una ejecución cortada.
    marker.write_text(json.dumps({"username": username}))
    marker.chmod(0o600)
    try:
        run(["/usr/sbin/useradd", "--create-home", "--user-group", "--shell", "/bin/bash", "--groups", group, username])
        run(["/usr/sbin/chpasswd"], f"{username}:{password}\n")
        if helper == "ctf-ssh-lab":
            account = pwd.getpwnam(username)
            target = Path(account.pw_dir) / "flag.txt"
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
            with os.fdopen(fd, "w") as output: output.write(data + "\n")
            os.chown(target, account.pw_uid, account.pw_gid)
        return {"username": username}
    except Exception:
        # El marcador queda disponible para destroy idempotente.
        raise


def main():
    if os.geteuid() != 0: raise ValueError()
    helper = Path(sys.argv[0]).name
    if helper not in ("ctf-ssh-lab", "ctf-dvwa-lab", "ctf-kali-session") or len(sys.argv) != 3: raise ValueError()
    action, run_id = sys.argv[1:]
    if action not in ("create", "check", "destroy") or not re.fullmatch(r"[a-f0-9]{12}", run_id): raise ValueError()
    # No leer stdin en check/destroy: evita el bloqueo encontrado anteriormente.
    data = sys.stdin.readline(257).rstrip("\n") if action == "create" else ""
    if len(data) > 256: raise ValueError()
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / "helper.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print(json.dumps(process(helper, action, run_id, data)))


if __name__ == "__main__":
    try: main()
    except Exception:
        print("La operación del laboratorio no se completó", file=sys.stderr)
        raise SystemExit(1)
