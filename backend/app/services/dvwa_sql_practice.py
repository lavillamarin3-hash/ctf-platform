"""Flag SQL dinámica en DVWA, exclusivamente LAB-SRVWEB de Nutanix AHV.

Nunca modifica la base dvwa. La cuenta labops solo puede invocar el
script remoto restringido; la clave del sistema se administra fuera de Git.
"""
from __future__ import annotations

import asyncio
from ipaddress import ip_address

from ..core import get_settings, submission_fingerprint

CODE = "ESC-03-WEBEXPLOIT"
SCENARIO = "DVWA-SQLI-LAB"
STRATEGY = "dvwa_sql_lab"
TARGET = "10.10.30.20"
PORT = 80
OFFSET = 1_000_000
REMOTE_SCRIPT = "/usr/local/sbin/ctf-dvwa-flag"


def supports(challenge) -> bool:
    return challenge.code == CODE and challenge.scenario == SCENARIO


def row_id(run_id: int) -> int:
    if type(run_id) is not int or not 1 <= run_id <= 2_145_483_647:
        raise ValueError("Identificador de corrida inválido")
    return OFFSET + run_id


def flag_for(run) -> str:
    return "FLAG{dvwa_sql_" + submission_fingerprint(
        f"dvwa-sql:flag:{run.user_id}:{run.id}")[:40] + "}"


def instructions(run) -> dict:
    return {
        "target": TARGET, "port": PORT, "path": "/dvwa/",
        "run_id": run.id, "row_id": row_id(run.id),
        "mission": "Desde Kali, inicia sesión en DVWA, selecciona el nivel Low y "
                   "encuentra la flag de tu fila de corrida en ctf_app_db.secrets con SQL Injection.",
        "note": "Solo LAB-SRVWEB, sin atacar SSH ni otras VMs. El servidor conserva "
                "la fila 1 de comprobación y las filas de otras corridas. "
                "Cierra el reto para eliminar solo tu fila.",
    }


def _write_remote(action: str, run_id: int, flag: str | None = None) -> None:
    import paramiko

    settings = get_settings()
    if not settings.dvwa_lab_enabled:
        raise RuntimeError("DVWA no habilitado por el administrador")
    if ip_address(TARGET).is_global:
        raise RuntimeError("El destino debe ser privado")
    if not settings.dvwa_lab_ssh_private_key or not settings.dvwa_lab_known_hosts:
        raise RuntimeError("DVWA requiere clave SSH y known_hosts dedicados")
    if action not in ("upsert", "delete"):
        raise ValueError("Acción de laboratorio inválida")
    record = row_id(run_id)
    if action == "upsert" and (not flag or not flag.startswith("FLAG{dvwa_sql_")):
        raise ValueError("Flag de laboratorio inválida")

    client = paramiko.SSHClient()
    client.load_host_keys(settings.dvwa_lab_known_hosts)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(
            hostname=TARGET, port=22, username=settings.dvwa_lab_ssh_user,
            key_filename=settings.dvwa_lab_ssh_private_key,
            timeout=8, auth_timeout=8, banner_timeout=8,
            allow_agent=False, look_for_keys=False,
        )
        command = f"sudo -n {REMOTE_SCRIPT} --{action} {record}"
        stdin, stdout, stderr = client.exec_command(command, timeout=12)
        if action == "upsert":
            stdin.write(flag + "\n")
            stdin.flush()
        stdin.channel.shutdown_write()
        code = stdout.channel.recv_exit_status()
        if code:
            raise RuntimeError("DVWA no confirmó la operación sobre la fila de la corrida")
    except Exception as exc:
        # No incluir contraseñas, contenido remoto, flag ni stderr en respuestas.
        raise RuntimeError("No fue posible preparar o limpiar la evidencia SQL en LAB-SRVWEB") from exc
    finally:
        client.close()


async def prepare(run) -> None:
    await asyncio.to_thread(_write_remote, "upsert", run.id, flag_for(run))


async def cleanup(run) -> None:
    await asyncio.to_thread(_write_remote, "delete", run.id)
