"""Conversión explícita e idempotente de cuatro retos a servicios VM."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..models import Challenge, ChallengeGroupAssignment, StudentGroup
from ..api.challenges import require_idle_challenge
from .bootstrap import write_audit
from .vm_logic import CODES, EXPECTED_SCENARIOS
from .challenge_deletion import deleted_codes

SPECS = {
    'WEB-02': {'name': 'Autenticación web · fallo lógico en vivo', 'difficulty': 'Medio',
        'description': 'Investiga un cliente web, prueba el fallo lógico de autenticación del servicio en LNX-VICT y demuestra una sesión autorizada con contraseña incorrecta.',
        'instructions': 'Desde Kali explora la URL inicial, inspecciona el cliente de referencia y compara solicitudes autorizadas y denegadas. Recupera el identificador de sesión y el rol que permitió el acceso. El servicio reproduce un fallo lógico únicamente sobre datos de práctica; no modifica cuentas del sistema.'},
    'WEB-06': {'name': 'Autorización de objetos · API vulnerable en vivo', 'difficulty': 'Medio',
        'description': 'Desde Kali correlaciona documentos de una API en LNX-VICT y demuestra el acceso a un objeto perteneciente a otro usuario.',
        'instructions': 'Consulta tu perfil y tus documentos. Sigue la referencia del mismo caso, identifica qué comprobación de propiedad falta y recupera el objeto ajeno. Entrega su ID, propietario y evidencia. No confundas documentos históricos ni objetos de tu propia cuenta.'},
    'FOR-05': {'name': 'Integridad forense · adquisición desde la víctima', 'difficulty': 'Medio',
        'description': 'Adquiere un manifiesto y ocho artefactos desde LNX-VICT, conserva sus bytes y determina la alteración comparando SHA-256 en Kali.',
        'instructions': 'Explora el portal remoto y adquiere el manifiesto y sus artefactos. Calcula los hashes de los archivos descargados en Kali y compáralos con los de adquisición. Entrega el nombre del único archivo alterado, su SHA-256 de adquisición y el SHA-256 observado.'},
    'DFIR-01': {'name': 'La exportación fuera de ventana · investigación desde la víctima', 'difficulty': 'Avanzado',
        'description': 'Adquiere fuentes forenses desde LNX-VICT, verifica su integridad, calibra relojes y reconstruye una exportación correlacionando autenticación, HTTP y red.',
        'instructions': 'Desde Kali adquiere manifiesto, Auth, HTTP, red y calibración de la URL inicial. Verifica los hashes antes de analizar. Encuentra la única sesión con MFA omitido, exportación HTTP exitosa superior a 500000 bytes y transferencia a 203.0.113.77 en menos de 60 segundos desde la autenticación real. Corrige los desfases constantes con las dos balizas. Entrega sesión, usuario, request, destino y autenticación UTC.'},
}


async def configure(session, group_code='45HY'):
    permanently_deleted = await deleted_codes(session)
    expected = set(CODES) - permanently_deleted
    group = await session.scalar(select(StudentGroup).where(StudentGroup.code == group_code,
        StudentGroup.is_active.is_(True)).with_for_update())
    if group is None:
        raise ValueError('El grupo activo solicitado no existe')
    challenges = (await session.scalars(select(Challenge).options(selectinload(Challenge.flags))
        .where(Challenge.code.in_(CODES)).order_by(Challenge.id).with_for_update())).all()
    challenges = [challenge for challenge in challenges if challenge.code in expected]
    if {challenge.code for challenge in challenges} != expected:
        raise ValueError('Faltan retos existentes del lote VM')
    changed = []
    for challenge in challenges:
        active = [flag for flag in challenge.flags if flag.is_active]
        if len(active) != 1 or active[0].mode != 'dynamic' or not active[0].template:
            raise ValueError('Cada reto requiere exactamente una flag dinámica activa')
        desired = {**SPECS[challenge.code], 'scenario': EXPECTED_SCENARIOS[challenge.code],
                   'asset_references': ['LAB-KALI', 'LAB-LNXVICT']}
        if any(getattr(challenge, key) != value for key, value in desired.items()):
            await require_idle_challenge(session, challenge.id)
            before = {key: getattr(challenge, key) for key in desired}
            await write_audit(session, None, 'challenge.vm_logic.convert', 'challenge', str(challenge.id),
                              {'code': challenge.code, 'before': before})
            for key, value in desired.items():
                setattr(challenge, key, value)
            changed.append(challenge.code)
        challenge.is_published = True
        assigned = await session.scalar(select(ChallengeGroupAssignment.id).where(
            ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group.id))
        if assigned is None:
            session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
            await write_audit(session, None, 'challenge.group.assign', 'challenge', str(challenge.id),
                              {'code': challenge.code, 'group_id': group.id})
    await session.flush()
    return {'group': group.code, 'changed': changed, 'vm_logic': [code for code in CODES if code in expected]}
