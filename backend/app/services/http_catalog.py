"""Publicación explícita de dos prácticas HTTP sobre las VMs existentes."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import Challenge, ChallengeFlag, ChallengeGroupAssignment, StudentGroup
from ..api.challenges import require_idle_challenge
from .bootstrap import write_audit
from .challenge_deletion import deleted_codes


SPECS = {
    'ESC-06-WEBAUTH': {
        'name': 'Adivinación de contraseña web · HTTP real',
        'description': 'Desde Kali descubre la contraseña de una cuenta temporal HTTP Basic en LNX-VICT y recupera su flag.',
        'instructions': 'Inicia el reto y trabaja desde Kali. Investiga la respuesta del recurso privado de la cuenta HTTP Basic, prepara un diccionario con los doce candidatos y construye una prueba acotada con Hydra. Comprueba el acceso usando la contraseña encontrada, recupera la flag y cierra el reto. Las ayudas de la plataforma son opcionales y la cuenta caduca según el plazo configurado que muestra el contador del reto.',
        'difficulty': 'Medio', 'points': 250,
        'scenario': 'HTTP-PASSWORD-LAB',
        'mitre_technique': 'T1110.001 — Password Guessing',
    },
    'ESC-07-EXPOSED': {
        'name': 'Respaldos expuestos · versiones, integridad y reconstrucción',
        'description': 'Desde Kali descubre respaldos en LNX-VICT, selecciona la versión íntegra entre señuelos y reconstruye una evidencia fragmentada.',
        'instructions': 'Explora la URL inicial desde Kali y sigue las pistas públicas del sitio. Correlaciona versión y SHA-256 del manifiesto con los respaldos, conserva los bytes y reconstruye la evidencia ordenando sus fragmentos y aplicando la transformación indicada. Entrega nombre del respaldo, release y evidencia. No hay una flag directa en un archivo. Las rutas y los datos cambian por corrida; el cierre o caducidad invalida el servicio.',
        'difficulty': 'Medio', 'points': 150,
        'scenario': 'HTTP-EXPOSED-FILES-LAB',
        'mitre_technique': 'T1595 — Active Scanning',
    },
}


async def configure(session, group_code='45HY'):
    permanently_deleted = await deleted_codes(session)
    group = await session.scalar(select(StudentGroup).where(
        StudentGroup.code == group_code, StudentGroup.is_active.is_(True)).with_for_update())
    if group is None:
        raise ValueError('El grupo activo solicitado no existe')
    challenges = (await session.scalars(select(Challenge).options(selectinload(Challenge.flags))
                   .where(Challenge.code.in_(SPECS)).with_for_update())).all()
    by_code = {challenge.code: challenge for challenge in challenges}
    created = []
    changed = []
    for code, spec in SPECS.items():
        if code in permanently_deleted:
            continue
        challenge = by_code.get(code)
        if challenge is None:
            challenge = Challenge(code=code, category='WEB', asset_references=['LAB-KALI', 'LAB-LNXVICT'],
                                  is_published=True, **spec)
            challenge.flags = [ChallengeFlag(label='Evidencia web por corrida', mode='dynamic',
                               template='FLAG{http_practice_{{RAND}}}', flag_order=1, is_active=True)]
            session.add(challenge)
            await session.flush()
            created.append(code)
            await write_audit(session, None, 'challenge.create', 'challenge', str(challenge.id),
                              {'code': code, 'scenario': spec['scenario'], 'source': 'owner-requested HTTP VM exercise'})
        else:
            active_flags = [flag for flag in challenge.flags if flag.is_active]
            if (challenge.scenario != spec['scenario']
                    or challenge.asset_references != ['LAB-KALI', 'LAB-LNXVICT']
                    or len(active_flags) != 1 or active_flags[0].mode != 'dynamic'
                    or not active_flags[0].template):
                raise ValueError('El código ya existe con otra configuración: ' + code)
            content = {key: value for key, value in spec.items() if key != 'points'}
            if any(getattr(challenge, key) != value for key, value in content.items()):
                await require_idle_challenge(session, challenge.id)
                before = {key: getattr(challenge, key) for key in content}
                await write_audit(session, None, 'challenge.http.enrich', 'challenge', str(challenge.id),
                                  {'code': code, 'before': before})
                for key, value in content.items():
                    setattr(challenge, key, value)
                changed.append(code)
            if not challenge.is_published:
                challenge.is_published = True
                await write_audit(session, None, 'challenge.publish', 'challenge', str(challenge.id), {'code': code})
        assigned = await session.scalar(select(ChallengeGroupAssignment.id).where(
            ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group.id))
        if assigned is None:
            session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
            await write_audit(session, None, 'challenge.group.assign', 'challenge', str(challenge.id),
                              {'code': code, 'group_id': group.id})
    await session.flush()
    return {'group': group.code, 'created': created, 'changed': changed,
            'published_assigned': [code for code in SPECS if code not in permanently_deleted]}
