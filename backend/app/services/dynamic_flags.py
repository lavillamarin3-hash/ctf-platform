"""Orquestación de flags dinámicas sin acoplar el dominio a SSH o PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from sqlalchemy import select

from ..core import get_settings, hash_password, submission_fingerprint, verify_password
from ..domain.flags.service import FlagService
from ..domain.ports.flag_injector import FlagInjectorGateway
from ..models import AuditEvent, Challenge, ChallengeFlag, ChallengeRun, ChallengeRunFlag, VMAsset
from .runtime_flags import effective_mode_template, is_effectively_dynamic


REPRODUCIBLE_CODES = frozenset(('LAB-01', 'ESC-01-RECON'))
DERIVATION_ACTION = 'challenge_run.flag_derivation'
DERIVATION_SCHEME = 'shared-lab-hmac-v1'


def reproducible_value(template, *, code, username, run, flag_id, flag_order, service=None):
    """Expande la misma plantilla con 128 bits HMAC exclusivos de esta evidencia.

    El servicio de dominio conserva su generación aleatoria predeterminada;
    únicamente estos dos retos reemplazan RAND antes de llamarlo.
    """
    context = {'scheme': DERIVATION_SCHEME, 'code': code, 'username': username,
               'user_id': run.user_id, 'challenge_id': run.challenge_id,
               'run_id': run.id, 'flag_id': flag_id, 'flag_order': flag_order, 'template': template}
    random_part = submission_fingerprint('shared-lab-flag:' + json.dumps(
        context, sort_keys=True, ensure_ascii=True, separators=(',', ':')))[:32]
    return (service or FlagService()).render_template(
        template.replace('{{RAND}}', random_part), code=code, username=username, run_id=run.id)


async def restored_run_answers(session, run):
    """Solo reconstruye una corrida marcada y cuyo hash sigue coincidiendo."""
    if run.workspace_strategy != 'shared_lab_vm':
        return None
    marker = await session.scalar(select(AuditEvent).where(
        AuditEvent.action == DERIVATION_ACTION, AuditEvent.entity_type == 'challenge_run',
        AuditEvent.entity_id == str(run.id), AuditEvent.actor_id == run.user_id,
    ).order_by(AuditEvent.id.desc()).limit(1))
    if marker is None:
        return None
    data = marker.details
    if (not isinstance(data, dict) or data.get('scheme') != DERIVATION_SCHEME
            or data.get('code') not in REPRODUCIBLE_CODES or data.get('challenge_id') != run.challenge_id
            or not isinstance(data.get('username'), str) or not isinstance(data.get('flags'), list)
            or not 1 <= len(data['flags']) <= 10):
        return None
    stored = {flag.flag_id: flag for flag in (await session.scalars(select(ChallengeRunFlag).where(
        ChallengeRunFlag.run_id == run.id))).all()}
    specs = data['flags']
    if any(not isinstance(spec, dict) or type(spec.get('flag_id')) is not int
           or type(spec.get('flag_order')) is not int or not isinstance(spec.get('template'), str)
           for spec in specs):
        return None
    if len(stored) != len(specs) or set(stored) != {spec['flag_id'] for spec in specs}:
        return None
    answers = []
    for spec in sorted(specs, key=lambda item: (item['flag_order'], item['flag_id'])):
        try:
            value = reproducible_value(spec['template'], code=data['code'], username=data['username'],
                                       run=run, flag_id=spec['flag_id'], flag_order=spec['flag_order'])
        except (ValueError, TypeError):
            return None
        # Una clave rotada, metadatos editados o una corrida legacy nunca deben
        # producir una respuesta inventada: el hash de validación es la autoridad.
        if not verify_password(value, stored[spec['flag_id']].flag_hash):
            return None
        answers.append(value)
    return answers


@dataclass(frozen=True)
class PreparedDynamicFlag:
    """Metadatos mínimos que se necesitan para limpiar la evidencia."""

    flag_id: int
    order: int
    path: str


class DynamicFlagRuntime:
    """Genera, persiste por hash, inyecta y limpia flags de una ejecución."""

    def __init__(self, injector: FlagInjectorGateway, flag_service: FlagService | None = None) -> None:
        self.injector = injector
        self.flags = flag_service or FlagService()
        self.settings = get_settings()

    def path_for(self, flag: ChallengeFlag, challenge_code: str) -> str:
        # Este escenario comparte VM con LAB-01, pero nunca su archivo de flag.
        # LAB-01 conserva la ruta heredada para no alterar corridas existentes.
        template = (
            "/opt/ctf/ESC-01-RECON/flag.txt"
            if challenge_code == "ESC-01-RECON"
            else self.settings.flag_injector_flag_path
        )
        if "{{CODE}}" in template:
            if not re.fullmatch(r"[A-Z0-9-]{3,64}", challenge_code):
                raise ValueError("El código del reto no es válido para una ruta de flag")
            template = template.replace("{{CODE}}", challenge_code)
        path = template.replace("{{ORDER}}", str(flag.flag_order))
        if (not path.startswith("/opt/ctf/") or path.endswith("/")
                or any(part in ("", ".", "..") for part in path.split("/")[3:])
                or "{{" in path or "}}" in path or any(ord(char) < 32 for char in path)):
            raise ValueError("FLAG_INJECTOR_FLAG_PATH debe apuntar a un archivo dentro de /opt/ctf")
        return path

    async def prepare(
        self,
        session,
        challenge: Challenge,
        run: ChallengeRun,
        username: str,
        target_vm: VMAsset | None,
    ) -> list[PreparedDynamicFlag]:
        dynamic_flags = [flag for flag in challenge.flags if is_effectively_dynamic(challenge.code, flag)]
        if not dynamic_flags:
            return []
        if target_vm is None or not target_vm.ip_address:
            raise ValueError("El reto dinámico necesita una VM víctima con IP asignada")
        if not self.settings.flag_injector_enabled:
            raise ValueError("El inyector SSH está deshabilitado; activa FLAG_INJECTOR_ENABLED para un reto dinámico")
        if challenge.code == "ESC-01-RECON" and len(dynamic_flags) > 1:
            raise ValueError("ESC-01-RECON admite una sola flag dinámica de evidencia")
        if len(dynamic_flags) > 1 and "{{ORDER}}" not in self.settings.flag_injector_flag_path:
            raise ValueError("Hay varias flags dinámicas activas. Usa FLAG_INJECTOR_FLAG_PATH con {{ORDER}} para darles archivos distintos")

        prepared: list[PreparedDynamicFlag] = []
        derivation_specs = []
        for flag in sorted(dynamic_flags, key=lambda item: item.flag_order):
            path = self.path_for(flag, challenge.code)
            _mode, template = effective_mode_template(challenge.code, flag)
            if not template:
                raise ValueError(f"La flag dinámica {flag.label or flag.id} no tiene plantilla efectiva")
            if challenge.code in REPRODUCIBLE_CODES:
                clear_value = reproducible_value(template, code=challenge.code, username=username,
                    run=run, flag_id=flag.id, flag_order=flag.flag_order, service=self.flags)
                derivation_specs.append({'flag_id': flag.id, 'flag_order': flag.flag_order, 'template': template})
            else:
                clear_value = self.flags.render_template(
                    template, code=challenge.code, username=username, run_id=run.id)
            await self.injector.inject(target_vm.ip_address, path, clear_value, target_vm.os)
            session.add(
                ChallengeRunFlag(
                    run_id=run.id,
                    flag_id=flag.id,
                    flag_hash=hash_password(clear_value),
                    fingerprint=submission_fingerprint(clear_value),
                )
            )
            prepared.append(PreparedDynamicFlag(flag_id=flag.id, order=flag.flag_order, path=path))
        if derivation_specs:
            # Contexto original, sin clave ni flag en claro. Se confirma junto
            # a ChallengeRunFlag o se revierte con el inicio fallido.
            session.add(AuditEvent(actor_id=run.user_id, action=DERIVATION_ACTION,
                entity_type='challenge_run', entity_id=str(run.id), details={
                    'scheme': DERIVATION_SCHEME, 'code': challenge.code,
                    'challenge_id': challenge.id, 'username': username, 'flags': derivation_specs}))
        return prepared

    async def cleanup(
        self,
        session,
        run_id: int,
        challenge: Challenge,
        target_vm: VMAsset | None,
    ) -> None:
        """Limpia únicamente las rutas de flags dinámicas usadas por la ejecución."""
        if target_vm is None or not target_vm.ip_address:
            return
        dynamic_ids = {
            flag.id: flag
            for flag in challenge.flags
            if is_effectively_dynamic(challenge.code, flag)
        }
        if not dynamic_ids:
            return
        # Limpia por las rutas efectivas, no solo por las filas ChallengeRunFlag.
        # Es necesario para recuperarse de una inyección parcial seguida de rollback.
        for flag in sorted(dynamic_ids.values(), key=lambda item: item.flag_order):
            await self.injector.clear(target_vm.ip_address, self.path_for(flag, challenge.code), target_vm.os)
