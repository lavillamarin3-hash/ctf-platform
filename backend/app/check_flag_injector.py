"""Chequeo NO DESTRUCTIVO de inyección SSH y servicio didáctico en LAB-LNXVICT.

Uso en el contenedor backend:
    python -m app.check_flag_injector

No genera, lee ni muestra banderas. No modifica VMs, permisos ni datos.
"""
from __future__ import annotations

import asyncio
import json
import shlex

from .core import get_settings
from .infrastructure.injection.ssh import SSHFlagInjector

VICTIM_IP = "10.10.30.12"


def remote_prerequisites() -> dict[str, bool]:
    # Reutilizar el mismo adaptador de credenciales de la API.
    from .services.ssh_practice import connection

    checks: dict[str, bool] = {}
    with connection() as client:
        commands = {
            "ssh_sftp": None,
            "python3_en_victima": "command -v python3 >/dev/null 2>&1",
            "paramiko_en_victima": 'python3 -c "import paramiko" >/dev/null 2>&1',
            "inyector_instalado": "test -f /usr/local/sbin/ctf-inject-flag.sh",
            "sudo_sin_password": (
                "sudo -n -l " + shlex.quote(get_settings().flag_injector_remote_script)
                + " >/dev/null 2>&1"
            ),
        }
        for name, command in commands.items():
            try:
                if command is None:
                    with client.open_sftp():
                        pass
                    checks[name] = True
                else:
                    _, out, _ = client.exec_command(command, timeout=8)
                    checks[name] = out.channel.recv_exit_status() == 0
            except Exception:
                checks[name] = False
    return checks


async def main() -> int:
    settings = get_settings()
    report: dict = {
        "target": "LAB-LNXVICT (10.10.30.12)",
        "checks": {
            "inyector_activado": settings.flag_injector_enabled,
            "credencial_ssh_configurada": bool(
                settings.flag_injector_ssh_private_key or settings.flag_injector_ssh_password
            ),
            "host_key_estricta": settings.flag_injector_strict_host_key,
        },
        "notes": [],
    }
    if not settings.flag_injector_strict_host_key:
        report["notes"].append(
            "IMPORTANTE: configura known_hosts y FLAG_INJECTOR_STRICT_HOST_KEY=true"
        )
    if not settings.flag_injector_enabled or not report["checks"]["credencial_ssh_configurada"]:
        report["notes"].append("Configura el inyector en el .env privado antes de probar el reto")
    else:
        injector = SSHFlagInjector()
        try:
            await injector.preflight(VICTIM_IP)
            report["checks"]["tcp_ssh_desde_api"] = True
        except Exception:
            report["checks"]["tcp_ssh_desde_api"] = False
            report["notes"].append("No llega TCP/22 a LAB-LNXVICT desde el contenedor API")
        if report["checks"]["tcp_ssh_desde_api"]:
            try:
                await injector.probe_authentication(VICTIM_IP)
                report["checks"]["autenticacion_ssh"] = True
            except Exception:
                report["checks"]["autenticacion_ssh"] = False
                report["notes"].append("El usuario configurado no pudo autenticarse; comprueba SSH/known_hosts")
            if report["checks"].get("autenticacion_ssh"):
                try:
                    report["checks"].update(await asyncio.to_thread(remote_prerequisites))
                except Exception:
                    report["notes"].append("No se pudo comprobar los componentes remotos")
    required = ("inyector_activado", "credencial_ssh_configurada", "tcp_ssh_desde_api",
                "autenticacion_ssh", "ssh_sftp", "inyector_instalado", "sudo_sin_password")
    report["ready_for_flag_injection"] = all(report["checks"].get(key) for key in required)
    report["ready_for_ssh_practice"] = (
        report["ready_for_flag_injection"]
        and report["checks"].get("python3_en_victima")
        and report["checks"].get("paramiko_en_victima")
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ready_for_flag_injection"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
