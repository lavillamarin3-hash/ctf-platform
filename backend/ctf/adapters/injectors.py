import asyncio
import ipaddress
import json
from pathlib import Path
from ..domain.laboratory import validate_run_id, RecursoNoDisponibleError

SCRIPTS = {"/usr/local/sbin/ctf-ssh-lab": {"10.10.30.12"},
           "/usr/local/sbin/ctf-dvwa-lab": {"10.10.30.20"},
           "/usr/local/sbin/ctf-kali-session": {"10.10.20.10", "10.10.20.11", "10.10.20.12"}}


class SshInjector:
    def __init__(self, settings): self.settings = settings

    async def verify_session(self, host, run_id, password):
        validate_run_id(run_id)
        if host not in SCRIPTS["/usr/local/sbin/ctf-kali-session"] or not self.settings.ssh_injector_enabled:
            raise RecursoNoDisponibleError()
        import asyncssh
        try:
            async with asyncio.timeout(20):
                async with asyncssh.connect(host, port=22, username=f"ctf_{run_id}", password=password, client_keys=[],
                                            known_hosts=self.settings.ssh_injector_known_hosts, agent_path=None, config=None):
                    pass  # Autenticación real, sin ejecutar comandos libres.
        except Exception:
            raise RecursoNoDisponibleError() from None

    async def execute(self, host, script, action, run_id, data=""):
        validate_run_id(run_id)
        if str(ipaddress.ip_address(host)) not in SCRIPTS.get(script, set()) or action not in ("create", "check", "destroy"):
            raise RecursoNoDisponibleError()
        s = self.settings
        if not s.ssh_injector_enabled or (script.endswith("ctf-dvwa-lab") and not s.dvwa_lab_enabled):
            raise RecursoNoDisponibleError()
        if not Path(s.ssh_injector_known_hosts).is_file() or not Path(s.ssh_injector_key_path).is_file():
            raise RecursoNoDisponibleError()
        import asyncssh
        try:
            async with asyncio.timeout(25):
                async with asyncssh.connect(host, username=s.ssh_injector_user, port=22, client_keys=[s.ssh_injector_key_path],
                                            known_hosts=s.ssh_injector_known_hosts, agent_path=None, config=None) as connection:
                    # Valores limitados por listas cerradas y regex; flag solo stdin.
                    result = await connection.run(f"sudo -n {script} {action} {run_id}", input=data + "\n" if data else "", check=True)
                    output = json.loads(result.stdout or "{}")
                    if not isinstance(output, dict): raise ValueError()
                    return output
        except Exception:
            raise RecursoNoDisponibleError() from None


class WinRmInjector:
    """Puerto preparado, cerrado hasta verificar ruta y stdin del helper Windows.

    No se envía una flag en argumentos/PowerShell codificado: pywinrm.run_ps
    no cumple ese contrato. La implementación de transporte requiere validar
    Send stdin del protocolo y el helper de WINVICT-A→B antes de habilitarlo.
    """
    async def execute(self, host, script, action, run_id, data=""):
        validate_run_id(run_id)
        raise RecursoNoDisponibleError()

    async def verify_session(self, host, run_id, password):
        raise RecursoNoDisponibleError()
