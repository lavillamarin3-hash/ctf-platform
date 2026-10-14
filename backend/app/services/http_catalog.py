"""Publicación explícita de dos prácticas HTTP sobre las VMs existentes."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import Challenge, ChallengeFlag, ChallengeGroupAssignment, StudentGroup
from .bootstrap import write_audit


SPECS = {
    'ESC-06-WEBAUTH': {
        'name': 'Adivinación de contraseña web · HTTP real',
        'description': 'Desde Kali descubre la contraseña de una cuenta temporal HTTP Basic en LNX-VICT y recupera su flag.',
        'instructions': 'Inicia el reto y trabaja en la terminal Kali. La pantalla muestra la URL, el usuario temporal y 12 contraseñas de práctica. Crea el diccionario y ejecuta Hydra con el comando indicado. Usa la contraseña encontrada con curl --user para leer la evidencia. Envía la flag y cierra el reto. La cuenta caduca en una hora y se invalida al cerrar.',
        'difficulty': 'Medio', 'points': 250,
        'scenario': 'HTTP-PASSWORD-LAB',
        'mitre_technique': 'T1110.001 — Password Guessing',
    },
    'ESC-07-EXPOSED': {
        'name': 'Archivos expuestos · reconocimiento web real',
        'description': 'Desde Kali inspecciona robots.txt en LNX-VICT, descubre una carpeta de respaldo expuesta y recupera la evidencia.',
        'instructions': 'Inicia el reto y trabaja en la terminal Kali. Consulta robots.txt en la URL de la corrida. Sigue la ruta Disallow, revisa el listado de respaldo y descarga el archivo de evidencia indicado. Envía su flag y cierra el ejercicio. robots.txt es una pista pública y no restringe el acceso. El servicio publica únicamente archivos didácticos de esta corrida; caducan en una hora.',
        'difficulty': 'Básico', 'points': 150,
        'scenario': 'HTTP-EXPOSED-FILES-LAB',
        'mitre_technique': 'T1595 — Active Scanning',
    },
}


async def configure(session, group_code='45HY'):
    group = await session.scalar(select(StudentGroup).where(
        StudentGroup.code == group_code, StudentGroup.is_active.is_(True)).with_for_update())
    if group is None:
        raise ValueError('El grupo activo solicitado no existe')
    challenges = (await session.scalars(select(Challenge).options(selectinload(Challenge.flags))
                   .where(Challenge.code.in_(SPECS)).with_for_update())).all()
    by_code = {challenge.code: challenge for challenge in challenges}
    created = []
    for code, spec in SPECS.items():
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
    return {'group': group.code, 'created': created, 'published_assigned': list(SPECS)}
