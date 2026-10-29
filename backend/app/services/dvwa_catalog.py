"""Configurador opt-in: no se ejecuta al iniciar la API."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import Challenge, ChallengeFlag, ChallengeGroupAssignment, StudentGroup
from ..api.challenges import require_idle_challenge
from .bootstrap import write_audit
from .challenge_deletion import deleted_codes
from .dvwa_sql_practice import CODE, SCENARIO

SPEC = dict(
    name='DVWA: extraer evidencia SQL de la corrida',
    category='WEB',
    scenario=SCENARIO,
    description='Desde Kali aprovecha únicamente la inyección SQL de DVWA para leer tu fila de práctica en ctf_app_db.secrets.',
    instructions='Abre Kali y accede a http://10.10.30.20/dvwa/. Inicia sesión con la cuenta de laboratorio autorizada, fija DVWA Security en Low y trabaja solo en el módulo SQL Injection. Introduce una consulta UNION que recupere el campo flag desde ctf_app_db.secrets filtrando por el ID de tu corrida (visible en la guía de DVWA del reto). Copia esa flag y envíala a Cociber. Cierra el reto para eliminar solo tu evidencia.',
    difficulty='Medio',
    mitre_technique='T1190 — Exploit Public-Facing Application',
    asset_references=['LAB-KALI-PURPLE', 'LAB-SRVWEB'],
    points=250,
)


async def configure(session, group_code='45HY'):
    if CODE in await deleted_codes(session):
        raise ValueError('El reto está eliminado definitivamente')
    group = await session.scalar(select(StudentGroup).where(
        StudentGroup.code == group_code, StudentGroup.is_active.is_(True)).with_for_update())
    if group is None: raise ValueError('El grupo indicado no existe o está inactivo')
    challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags))
        .where(Challenge.code == CODE).with_for_update())
    created = challenge is None
    if created:
        challenge = Challenge(code=CODE, is_published=False, **SPEC)
        challenge.flags = [ChallengeFlag(label='Flag DVWA SQL por corrida', mode='dynamic',
            template='FLAG{dvwa_sql_{{RAND}}}', flag_order=1, is_active=True)]
        session.add(challenge)
        await session.flush()
    else:
        await require_idle_challenge(session, challenge.id)
        active = [flag for flag in challenge.flags if flag.is_active]
        if len(active) != 1 or active[0].mode != 'dynamic' or not active[0].template:
            raise ValueError('El reto existente no tiene exactamente una flag dinámica activa')
        # No destruir instrucciones personalizadas ni recompensas existentes.
        if challenge.scenario != SCENARIO or challenge.asset_references != SPEC['asset_references']:
            raise ValueError('El reto existente tiene una configuración incompatible')
    assigned = await session.scalar(select(ChallengeGroupAssignment.id).where(
        ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group.id))
    if assigned is None:
        session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
    await write_audit(session, None, 'challenge.dvwa.configure', 'challenge', str(challenge.id),
                      {'created': created, 'group': group_code})
    return {'created': created, 'code': CODE, 'group': group_code,
            'published': challenge.is_published, 'note': 'Publicar solo después de validación real'}
