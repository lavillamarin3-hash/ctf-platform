"""Registro explícito e idempotente del portal local Operación Cóndor.

No despliega servidores, no consulta URLs y no guarda credenciales ni flags en
claro. El operador verifica previamente el portal y proporciona su flag por un
canal privado. El llamador decide confirmar o revertir la transacción.
"""
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..core import hash_password, verify_password
from ..models import Challenge, ChallengeFlag, ChallengeGroupAssignment, StudentGroup
from ..schemas import LearningPolicy
from .bootstrap import write_audit
from .challenge_deletion import deleted_codes
from .external_web import ASSET_PREFIX, CODE, SCENARIO, TERMINAL_ASSET, normalize_portal_url, normalize_terminal_portal_url
from .runtime_flags import EXPLICIT_STATIC_VALIDATOR


POLICY = {
    'duration_minutes': 45,
    'expired_points_percent': 25,
    'hints': [
        {'title': 'Investiga antes de probar', 'penalty_percent': 10,
         'content': 'Revisa las noticias y la información pública del portal. Una publicación identifica la cuenta de demostración del centro de mando.'},
        {'title': 'Un diccionario acotado', 'penalty_percent': 10,
         'content': 'Encuentra y descarga el diccionario de doce candidatos del ejercicio. Observa el formulario de acceso y compara una respuesta fallida con una correcta. Solo prueba esos candidatos contra este portal de laboratorio.'},
        {'title': 'Demuestra el acceso', 'penalty_percent': 10,
         'content': 'Con la contraseña encontrada, inicia sesión en Acceso del personal. Abre el panel del administrador y publica un comunicado de auditoría. El portal mostrará la flag que debes enviar a Cociber CTF.'},
    ],
    'solution_text': ('Abre las noticias del portal y localiza la cuenta de demostración admin.condor. '
        'Descarga el diccionario de doce candidatos y observa cómo envía datos el formulario HTTP de acceso. '
        'Ensaya únicamente ese diccionario en el login del portal de práctica; identifica qué respuesta confirma el acceso. '
        'Inicia sesión con la contraseña encontrada, entra al centro de mando y publica un comunicado de auditoría. '
        'Copia la flag mostrada y envíala desde la corrida de Cociber CTF. '
        'El portal compartido sigue encendido al cerrar el reto.'),
}


TERMINAL_HINTS = [
    {'title': 'Descubre y adquiere',
     'content': 'Desde Kali identifica el servicio HTTP dentro de los puertos autorizados. Consulta robots.txt, sigue su referencia y descarga el manifiesto del respaldo. Conserva los archivos en la carpeta de tu corrida antes de analizarlos.'},
    {'title': 'Correlaciona el estado más reciente',
     'content': 'El manifiesto enlaza las cuentas y su bitácora, además del diccionario de candidatas. Une los registros por ID de cuenta y, para cada cuenta, aplica el estado del registro con mayor secuencia. Busca la cuenta que satisface simultáneamente el perfil y el estado exigidos por la regla de publicación; ignora nombres parecidos y estados antiguos. Conserva la correlación y explica por qué descartaste las demás cuentas.'},
    {'title': 'Prueba el formulario y demuestra el acceso',
     'content': 'Guarda el usuario obtenido de tu correlación en CONDOR_USER. Usa Hydra contra /login con ese usuario y el diccionario del respaldo, un intento simultáneo y el texto de error del formulario. Comprueba la contraseña iniciando una sesión HTTP con cookies y recoge el token CSRF del panel. Publica un comunicado con un título libre de 3 a 100 caracteres y un cuerpo de 10 a 1000 caracteres. Conserva evidencia del acceso y de la publicación; la flag aparece después de publicar.'},
]

TERMINAL_SOLUTION = (
    'En la terminal SSH de Kali crea una carpeta para tu corrida y ejecuta nmap -sT -Pn -p 18080-18090 contra la IP asignada.\n'
    'Construye BASE con la IP y el puerto HTTP descubierto. Usa curl para consultar "$BASE/robots.txt", sigue la referencia del respaldo y descarga su manifest.json.\n'
    'Lee el manifiesto con jq o Python y descarga las rutas que indican archivos.cuentas, archivos.bitacora y archivos.diccionario. No elijas una cuenta solo por su nombre.\n'
    'Agrupa la bitácora por ID de cuenta y selecciona el estado con mayor secuencia de cada cuenta. Une ese resultado con las cuentas y aplica simultáneamente perfil_requerido y estado_requerido de regla_publicacion. Guarda en CONDOR_USER el usuario del único candidato válido.\n'
    'Observa el formulario y confirma su texto de error. Ejecuta hydra -l "$CONDOR_USER" -P candidatas.txt -s "$PORT" -t 1 -f "$TARGET" http-post-form \'/login:username=^USER^&password=^PASS^:F=Credenciales incorrectas\' usando las doce candidatas adquiridas.\n'
    'Con curl, comprueba la contraseña iniciando sesión y guardando las cookies; solicita el panel /admin con esas cookies y extrae su token CSRF. Publica un comunicado en /admin/comunicados con el mismo token y sesión: elige un título libre de 3 a 100 caracteres y un cuerpo de 10 a 1000 caracteres.\n'
    'Vuelve a solicitar /admin, copia la flag que aparece después de publicar y envíala a Cociber CTF. Conserva evidencias de la correlación de cuentas, de la comprobación del acceso y del comunicado publicado. Explica los hallazgos y propone cómo corregirlos; no incluyas la contraseña, las cookies ni la flag en un informe público. Cerrar el reto no apaga el portal compartido.'
)

TERMINAL_INSTRUCTIONS = (
    'Objetivo: demostrar reconocimiento web, análisis de evidencias, comprobación de credenciales del laboratorio y publicación autenticada. Pulsa Iniciar y abre la terminal SSH de Kali integrada. Este ejercicio se resuelve con comandos contra la IP víctima y el rango de puertos indicados en la corrida. '
    'Descubre el servicio HTTP, investiga sus referencias públicas y adquiere el respaldo. Correlaciona las cuentas y su bitácora para determinar qué usuario cumple la regla de publicación. '
    'Prueba únicamente las doce candidatas del diccionario del laboratorio contra el formulario web de ese usuario. Comprueba la contraseña encontrada iniciando una sesión HTTP. Publica un comunicado con un título que tú elijas de 3 a 100 caracteres y un cuerpo de 10 a 1000 caracteres para obtener la flag; envíala a Cociber CTF. '
    'Conserva evidencias de cómo dedujiste el usuario, comprobaste el acceso y publicaste el comunicado. Entrega al tutor una explicación de los hallazgos y sus correcciones, sin exponer contraseñas, cookies ni flags en informes públicos. '
    'Usa una carpeta propia de tu corrida; Kali y el portal son compartidos. El contador empieza al iniciar, las pistas descuentan el porcentaje configurado y la explicación se habilita al vencer el plazo. '
    'Cerrar el reto cierra la terminal de tu corrida, pero no apaga la web ni reinicia los datos compartidos.'
)


def _terminal_policy(challenge):
    policy = LearningPolicy.model_validate(challenge.learning_policy or POLICY).model_dump()
    # El taller cambia el contenido didáctico; conserva cantidad, descuentos,
    # plazo y valoración de vencimiento elegidos por el instructor.
    policy['hints'] = [{**TERMINAL_HINTS[index], 'penalty_percent': hint['penalty_percent']}
                       for index, hint in enumerate(policy['hints'])]
    policy['solution_text'] = TERMINAL_SOLUTION
    return policy


async def upgrade_terminal(session, portal_url: str, group_code: str = '45HY', *, flag_value: str | None = None) -> dict:
    """Migración solicitada explícitamente; no crea retos.

    Conserva todos los resultados y snapshots de aprendizaje existentes. El
    llamador comprueba previamente el servidor y decide commit o rollback. La
    flag se conserva salvo que proporcione explícitamente el nuevo valor.
    """
    from ..api.challenges import require_idle_challenge

    normalized_url = normalize_terminal_portal_url(portal_url)
    if flag_value is not None and (not isinstance(flag_value, str) or not 12 <= len(flag_value) <= 200
                                  or any(ord(char) < 32 for char in flag_value)):
        raise ValueError('La nueva flag debe proporcionarse por el canal privado y tener de 12 a 200 caracteres.')
    group = await session.scalar(select(StudentGroup).where(
        StudentGroup.code == group_code, StudentGroup.is_active.is_(True)).with_for_update())
    if group is None:
        raise ValueError('El grupo activo solicitado no existe.')
    challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags))
        .where(Challenge.code == CODE).with_for_update())
    if challenge is None:
        if CODE in await deleted_codes(session):
            raise ValueError('El reto fue eliminado definitivamente. El taller SSH no lo recrea.')
        raise ValueError('Primero registra el reto existente; el taller SSH no crea retos ni flags.')
    if challenge.scenario != SCENARIO:
        raise ValueError('El código ya existe con otro escenario. No se modificó el reto.')
    flags = [flag for flag in challenge.flags if flag.is_active]
    if (len(flags) != 1 or flags[0].mode != 'static'
            or flags[0].validator != EXPLICIT_STATIC_VALIDATOR or not flags[0].flag_hash):
        raise ValueError('El taller SSH requiere la flag estática existente de su instalación.')
    await require_idle_challenge(session, challenge.id)
    rotate_flag = flag_value is not None and not verify_password(flag_value, flags[0].flag_hash)
    references = [ASSET_PREFIX + normalized_url, TERMINAL_ASSET]
    policy = _terminal_policy(challenge)
    desired = {'asset_references': references, 'instructions': TERMINAL_INSTRUCTIONS,
               'learning_policy': policy, 'is_published': True}
    changed = rotate_flag or any(getattr(challenge, key) != value for key, value in desired.items())
    if changed:
        before = {'asset_references': list(challenge.asset_references or []),
                  'is_published': challenge.is_published, 'points': challenge.points,
                  'duration_minutes': policy['duration_minutes'],
                  'expired_points_percent': policy['expired_points_percent'],
                  'hint_penalties': [hint['penalty_percent'] for hint in policy['hints']]}
        for key, value in desired.items():
            setattr(challenge, key, value)
        if rotate_flag:
            flags[0].flag_hash = hash_password(flag_value)
            await write_audit(session, None, 'flag.replace', 'flag', str(flags[0].id),
                {'challenge': CODE, 'mode': 'static', 'reason': 'explicit_condor_workshop_rotation'})
        await write_audit(session, None, 'challenge.condor.terminal_upgrade', 'challenge', str(challenge.id),
            {'code': CODE, 'before': before, 'flag_rotated': rotate_flag,
             'historical_progress_modified': False, 'content_updated': ['instructions', 'hints', 'solution']})
    assignment = await session.scalar(select(ChallengeGroupAssignment.id).where(
        ChallengeGroupAssignment.challenge_id == challenge.id,
        ChallengeGroupAssignment.group_id == group.id))
    if assignment is None:
        session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
        await write_audit(session, None, 'challenge.group.assign', 'challenge', str(challenge.id),
            {'code': CODE, 'group_id': group.id})
    await session.flush()
    return {'code': CODE, 'upgraded': changed, 'group': group.code, 'portal_url': normalized_url,
            'terminal_required': True, 'flag_rotated': rotate_flag, 'shared_portal': True,
            'published_assigned': True}


async def configure(session, portal_url: str, flag_value: str, group_code: str = '45HY') -> dict:
    normalized_url = normalize_portal_url(portal_url)
    if (not isinstance(flag_value, str) or not 12 <= len(flag_value) <= 200
            or any(ord(char) < 32 for char in flag_value)):
        raise ValueError('Proporciona la flag del portal por el canal privado: de 12 a 200 caracteres.')
    group = await session.scalar(select(StudentGroup).where(
        StudentGroup.code == group_code, StudentGroup.is_active.is_(True)).with_for_update())
    if group is None:
        raise ValueError('El grupo activo solicitado no existe.')
    challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags))
        .where(Challenge.code == CODE).with_for_update())
    created = challenge is None
    references = [ASSET_PREFIX + normalized_url]
    if challenge is None:
        if CODE in await deleted_codes(session):
            raise ValueError('El reto fue eliminado definitivamente. Este configurador no lo recrea automáticamente.')
        challenge = Challenge(code=CODE, name='Operación Cóndor: acceso al centro de mando',
            description='Simulación académica con datos ficticios. Investiga un portal militar inventado, descubre una contraseña débil y demuestra el acceso al panel del administrador.',
            instructions=('Pulsa Iniciar y abre el portal desde el botón del ejercicio. '
                'Este reto está en modo local y utiliza una web independiente y compartida; no necesita una terminal SSH o RDP. '
                'Revisa sus noticias, encuentra la cuenta de demostración y el diccionario acotado de doce candidatos. '
                'Prueba el acceso únicamente en ese portal, entra al centro de mando y publica un comunicado de auditoría. '
                'Envía la flag que muestra la web en el formulario de Cociber CTF. '
                'El contador empieza al iniciar; las pistas descuentan puntos y al vencer se habilita la solución. '
                'Cerrar el reto no apaga el portal ni reinicia sus datos compartidos.'),
            difficulty='Medio', category='WEB', scenario=SCENARIO,
            mitre_technique='T1110.001 — Password Guessing', points=250,
            asset_references=references, is_published=True, learning_policy=deepcopy(POLICY))
        challenge.flags = [ChallengeFlag(label='Evidencia del comunicado de auditoría',
            flag_hash=hash_password(flag_value), validator=EXPLICIT_STATIC_VALIDATOR,
            mode='static', template=None, flag_order=1, is_active=True)]
        session.add(challenge)
        await session.flush()
        await write_audit(session, None, 'challenge.create', 'challenge', str(challenge.id),
            {'code': CODE, 'scenario': SCENARIO, 'source': 'owner-requested independent local portal'})
    else:
        active_flags = [flag for flag in challenge.flags if flag.is_active]
        if (challenge.scenario != SCENARIO or challenge.asset_references != references
                or len(active_flags) != 1 or active_flags[0].mode != 'static'
                or active_flags[0].validator != EXPLICIT_STATIC_VALIDATOR
                or not active_flags[0].flag_hash
                or not verify_password(flag_value, active_flags[0].flag_hash)):
            raise ValueError('El código ya existe con otra configuración o flag. No se modificó el reto.')
        # Contenido, puntaje y política del instructor se conservan al repetir.
        if not challenge.is_published:
            challenge.is_published = True
            await write_audit(session, None, 'challenge.publish', 'challenge', str(challenge.id), {'code': CODE})
    assigned = await session.scalar(select(ChallengeGroupAssignment.id).where(
        ChallengeGroupAssignment.challenge_id == challenge.id,
        ChallengeGroupAssignment.group_id == group.id))
    if assigned is None:
        session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
        await write_audit(session, None, 'challenge.group.assign', 'challenge', str(challenge.id),
            {'code': CODE, 'group_id': group.id})
    await session.flush()
    return {'code': CODE, 'created': created, 'group': group.code, 'portal_url': normalized_url,
            'flag_mode': 'static', 'shared_portal': True, 'published_assigned': True}
