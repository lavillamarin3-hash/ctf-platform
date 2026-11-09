from dataclasses import dataclass
from enum import StrEnum
import hashlib
import hmac
import re
import secrets
from typing import Protocol


class DomainError(Exception):
    code = "VALIDATION_ERROR"
    message = "Revisa los datos de la operación."


class RecursoNoDisponibleError(DomainError):
    code = "RESOURCE_UNAVAILABLE"
    message = "El laboratorio no está disponible. Reintenta más tarde."


class CorridaYaActivaError(DomainError):
    code = "RUN_CONFLICT"
    message = "La corrida está ocupada o pendiente de limpieza."


class FlagIncorrectaError(DomainError):
    code = "INCORRECT_FLAG"
    message = "La bandera no corresponde a tu corrida."


class State(StrEnum):
    QUEUED = "en_cola"
    RESERVED = "reservada"
    ACTIVE = "activa"
    SOLVED = "resuelta"
    EXPIRED = "expirada"
    CANCELLED = "cancelada"
    CLEANING = "reiniciando"
    RELEASED = "liberada"


LIVE = (State.RESERVED, State.ACTIVE, State.CLEANING)
POINTS = {"basico": 100, "medio": 250, "avanzado": 500}
INSTRUCTIONS = {
    "SSH-PASSWORD-LAB": "Desde la Kali asignada, enumera SSH en LAB-LNXVICT:2222. El usuario es ctf_<run_id>. Prueba las 12 candidatas cociber01 a cociber12 y lee ~/flag.txt. El puerto 22 es administrativo y queda fuera del ejercicio.",
    "DVWA-SQLI-LAB": "Desde la Kali asignada abre http://10.10.30.20/dvwa/ con la cuenta de práctica entregada por el instructor. Configura seguridad Low, investiga SQL Injection y consulta ctf_app_db.secrets filtrando run_id por el identificador de tu corrida.",
    "RECON-SCAN-LAB": "Pendiente de validar el servicio de reconocimiento y su helper antes de habilitar la práctica.",
    "LATERAL-SMB-LAB": "Cadena confirmada LAB-WINVICT-A → LAB-WINVICT-B. Pendiente de validar el helper WinRM y la cuenta técnica.",
    "EXFIL-SMB-LAB": "Pendiente de confirmar el recurso Samba, las credenciales de práctica y su helper en LAB-SRVFSAD.",
}


@dataclass(frozen=True)
class Scenario:
    code: str
    strategy: str
    tag: str
    mitre: str
    difficulty: str
    victims: tuple[str, ...]
    script: str | None
    enabled: bool = False


SCENARIOS = (
    Scenario("ESC-01-RECON", "RECON-SCAN-LAB", "recon", "T1046", "basico", ("LAB-LNXVICT", "LAB-SRVWEB"), None),
    Scenario("ESC-02-BRUTEFORCE", "SSH-PASSWORD-LAB", "ssh", "T1110.001", "medio", ("LAB-LNXVICT",), "/usr/local/sbin/ctf-ssh-lab", True),
    Scenario("ESC-03-WEBEXPLOIT", "DVWA-SQLI-LAB", "dvwa_sql", "T1190", "medio", ("LAB-SRVWEB",), "/usr/local/sbin/ctf-dvwa-lab", True),
    # A→B confirmado por el usuario. Contrato WinRM todavía no validado.
    Scenario("ESC-04-LATERAL", "LATERAL-SMB-LAB", "lateral", "T1021.002", "avanzado", ("LAB-WINVICT-A", "LAB-WINVICT-B"), None),
    Scenario("ESC-05-EXFIL", "EXFIL-SMB-LAB", "exfil", "T1048", "avanzado", ("LAB-SRVFSAD",), None),
)


def scenario_for(strategy: str) -> Scenario:
    for item in SCENARIOS:
        if item.strategy == strategy:
            return item
    raise DomainError()


def validate_run_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{12}", value):
        raise DomainError()
    return value


def new_flag(strategy: str) -> str:
    return f"FLAG{{{scenario_for(strategy).tag}_{secrets.token_hex(20)}}}"


def flag_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_flag(value: str, expected: str) -> bool:
    return hmac.compare_digest(flag_hash(value.strip()), expected)


def validate_hints(hints: list[dict]) -> None:
    if len(hints) > 3 or any(not hint.get("text", "").strip() for hint in hints):
        raise DomainError()


class IFlagInjector(Protocol):
    async def execute(self, host: str, script: str, action: str, run_id: str, data: str = "") -> dict: ...
    async def verify_session(self, host: str, run_id: str, password: str) -> None: ...


class TerminalGateway(Protocol):
    async def create(self, run_id: str, host: str, password: str) -> str: ...
    async def destroy(self, run_id: str) -> None: ...
