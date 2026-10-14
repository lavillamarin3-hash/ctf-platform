"""Conversión explícita e idempotente; conserva flags antiguas, historial y puntuación."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..api.challenges import require_idle_challenge
from ..domain.challenges.offline import CATALOG
from ..models import Challenge, ChallengeFlag, ChallengeGroupAssignment, StudentGroup
from .bootstrap import write_audit

VERSION = 'OFFLINE-V1'


async def configure(session, group_code):
    group = await session.scalar(select(StudentGroup).where(StudentGroup.code == group_code, StudentGroup.is_active.is_(True)).with_for_update())
    if group is None:
        raise ValueError('El grupo activo solicitado no existe')
    challenges = (await session.scalars(select(Challenge).options(selectinload(Challenge.flags)).order_by(Challenge.id).with_for_update())).all()
    by_code = {c.code: c for c in challenges}
    missing = set(CATALOG) - set(by_code)
    if missing:
        raise ValueError('Faltan retos del catálogo: ' + ', '.join(sorted(missing)))
    # Validar todos antes de modificar cualquiera. No convertir una corrida en uso.
    for code in CATALOG:
        if by_code[code].scenario == 'SSH-PASSWORD-LAB': continue
        if by_code[code].scenario != VERSION:
            await require_idle_challenge(session, by_code[code].id)
    report = []
    for code, (title, kind, objective) in CATALOG.items():
        challenge = by_code[code]
        if challenge.scenario == 'SSH-PASSWORD-LAB':
            report.append({'code':code,'name':challenge.name,'mode':'ssh_password_lab'})
            continue
        if challenge.scenario != VERSION:
            before = {key: getattr(challenge, key) for key in ('name', 'description', 'instructions', 'scenario', 'asset_references', 'difficulty', 'is_published')}
            before['active_flag_ids'] = [f.id for f in challenge.flags if f.is_active]
            await write_audit(session, None, 'challenge.offline.convert', 'challenge', str(challenge.id), {'version': VERSION, 'before': before})
            for flag in challenge.flags:
                flag.is_active = False
            session.add(ChallengeFlag(challenge_id=challenge.id, label='Respuesta local por corrida', mode='dynamic', template='FLAG{offline_{{RAND}}}', flag_order=max((f.flag_order for f in challenge.flags), default=0)+1, is_active=True))
            challenge.name = title
            challenge.description = 'Ejercicio descargable con datos sintéticos. ' + objective
            challenge.instructions = ('Inicia una corrida y descarga el ZIP. Extrae los archivos y lee README.txt. ' + objective
                + ' Usa herramientas locales; no necesitas una VM ni contactar hosts. Valida la respuesta en el formulario, pulsa Registrar puntos y cierra el ejercicio. Dispones de cuatro horas; otra corrida genera nuevos datos. Los puntos se conceden una sola vez por reto.')
            challenge.asset_references = ['OFFLINE-CASE']
            challenge.scenario = VERSION
            challenge.difficulty = 'Medio' if kind in ('rsa', 'stego', 'validator', 'join', 'lateral', 'pcap', 'stack') else 'Básico'
        report.append({'code': code, 'name': challenge.name, 'mode': 'offline_case'})
    # Solo los 38 conocidos: no publicar accidentalmente borradores nuevos.
    for code in [*CATALOG, 'LAB-01', 'ESC-01-RECON', 'DFIR-01']:
        challenge = by_code.get(code)
        if challenge is None:
            raise ValueError('Falta el reto protegido ' + code)
        if not challenge.is_published:
            challenge.is_published = True
            await write_audit(session, None, 'challenge.publish', 'challenge', str(challenge.id), {'code': code})
        assigned = await session.scalar(select(ChallengeGroupAssignment.id).where(ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group.id))
        if assigned is None:
            session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
            await write_audit(session, None, 'challenge.group.assign', 'challenge', str(challenge.id), {'group_id': group.id, 'code': code})
    await session.flush()
    return {'group': group.code, 'converted': report, 'published_assigned': len(CATALOG)+3}
