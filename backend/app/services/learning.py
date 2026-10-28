"""Ayudas persistentes y valoración del aprendizaje: el servidor decide el puntaje.

La duración, las pistas y sus costes se fijan por usuario y reto al comenzar.
Cerrar/reabrir no reinicia el plazo ni las ayudas. Los ledgers anteriores sin
snapshot conservan 3x10%/25%; las finalizaciones otorgadas no se recalculan.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from fastapi import HTTPException
from sqlalchemy import select
from ..core import now_utc
from ..models import ChallengeCompletion, ChallengeHintReveal, ChallengeLearningProgress, ChallengeRun, User
from ..schemas import LearningPolicy
from ..domain.challenges.offline import CATALOG

POLICY_VERSION = 2
HINT_COUNT = 3


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def expired(progress, at=None):
    policy = getattr(progress, 'policy_snapshot', None)
    if isinstance(policy, dict) and policy.get('timer_enabled') is False:
        # TTL de la VM sigue vigente; no afecta al puntaje académico.
        return False
    return utc(at or now_utc()) >= utc(progress.deadline)


def expired_percent(progress):
    snapshot = getattr(progress, 'policy_snapshot', None)
    return snapshot['expired_points_percent'] if isinstance(snapshot, dict) else 25


def expired_points(progress):
    return progress.base_points * expired_percent(progress) // 100


def points_for(progress, hints_used=0, at=None):
    if expired(progress, at):
        return expired_points(progress)
    snapshot = getattr(progress, 'policy_snapshot', None)
    penalties = [hint['penalty_percent'] for hint in snapshot['hints']] if isinstance(snapshot, dict) else [10] * HINT_COUNT
    discount = sum(penalties[:min(len(penalties), max(0, hints_used))])
    return progress.base_points * max(0, 100 - discount) // 100


def _strategy_for(challenge):
    if challenge.code == 'WEB-CONDOR' and getattr(challenge, 'scenario', None) == 'CONDOR-WEB-LAB':
        return 'external_web_lab'
    if challenge.code == 'ESC-02-BRUTEFORCE' and getattr(challenge, 'scenario', None) == 'SSH-PASSWORD-LAB':
        return 'ssh_password_lab'
    if challenge.code == 'ESC-06-WEBAUTH':
        return 'http_password_lab'
    if challenge.code == 'ESC-07-EXPOSED':
        return 'http_files_lab'
    if str(getattr(challenge, 'scenario', '') or '').startswith('VM-LOGIC-'):
        return 'vm_logic_lab'
    references = getattr(challenge, 'asset_references', None) or []
    if 'DFIR-CASE' in references:
        return 'dfir_case'
    return 'offline_case' if 'OFFLINE-CASE' in references else 'shared_lab_vm'


def default_policy(challenge, *, strategy=None):
    strategy = strategy or _strategy_for(challenge)
    duration = 240 if strategy == 'offline_case' else 120 if strategy == 'dfir_case' else 60
    prototype = SimpleNamespace(id='{{RUN_ID}}', workspace_strategy=strategy)
    return {'duration_minutes': duration, 'expired_points_percent': 25, 'solution_text': None,
            'hints': [{'title': hint['title'], 'content': hint['content'], 'penalty_percent': 10}
                      for hint in _default_hints_for(prototype, challenge)]}


def effective_policy(challenge):
    configured = getattr(challenge, 'learning_policy', None)
    if isinstance(configured, dict):
        policy = LearningPolicy.model_validate(configured).model_dump()
        # Conservar instantáneas existentes sin añadir campos nuevos a retos antiguos.
        if 'timer_enabled' not in configured:
            policy.pop('timer_enabled', None)
        return policy
    return default_policy(challenge)


def policy_for_progress(progress, run, challenge):
    snapshot = getattr(progress, 'policy_snapshot', None)
    if isinstance(snapshot, dict):
        return deepcopy(snapshot)
    # Las corridas iniciadas antes de esta configuración conservan 3x10/25;
    # una edición de Challenge.learning_policy no se aplica retroactivamente.
    return default_policy(challenge, strategy=run.workspace_strategy)


async def plan_run(session, challenge, user, *, at=None):
    """Plazo físico real antes de crear servicios; no ampliar el plazo original."""
    at = utc(at or now_utc())
    await session.scalar(select(User.id).where(User.id == user.id).with_for_update())
    progress = await session.scalar(select(ChallengeLearningProgress).where(
        ChallengeLearningProgress.user_id == user.id, ChallengeLearningProgress.challenge_id == challenge.id,
    ).with_for_update())
    if progress is None:
        policy = effective_policy(challenge)
    else:
        policy = policy_for_progress(progress, SimpleNamespace(workspace_strategy=_strategy_for(challenge)), challenge)
        if getattr(progress, 'policy_snapshot', None) is None and progress.first_run_id is not None:
            first = await session.get(ChallengeRun, progress.first_run_id)
            if first is not None and first.started_at is not None:
                seconds = (utc(first.expires_at) - utc(first.started_at)).total_seconds()
                policy['duration_minutes'] = max(1, min(1440, round(seconds / 60)))
    expires_at = at + timedelta(minutes=policy['duration_minutes'])
    if progress is not None and utc(progress.deadline) > at:
        expires_at = min(expires_at, utc(progress.deadline))
    return expires_at, policy


async def lock_progress(session, run, challenge, *, create=False, required=False, policy=None):
    # Todos los caminos que afectan puntos usan este orden: usuario y ledger.
    # La fila del usuario serializa también la primera creación (aún sin ledger).
    await session.scalar(select(User.id).where(User.id == run.user_id).with_for_update())
    progress = await session.scalar(select(ChallengeLearningProgress).where(
        ChallengeLearningProgress.user_id == run.user_id,
        ChallengeLearningProgress.challenge_id == challenge.id,
    ).with_for_update())
    if progress is None and create:
        progress = ChallengeLearningProgress(user_id=run.user_id, challenge_id=challenge.id,
            first_run_id=run.id, policy_version=POLICY_VERSION, base_points=challenge.points,
            deadline=run.expires_at, is_assisted=False, policy_snapshot=deepcopy(policy or effective_policy(challenge)))
        session.add(progress)
        await session.flush()
    if required and (progress is None or (progress.first_run_id is not None and run.id < progress.first_run_id)):
        raise HTTPException(409, 'Las ayudas se activan en una nueva corrida. Cierra esta corrida e inicia otra; tus puntos previos se conservan.', headers={'Cache-Control': 'no-store'})
    if progress is not None and progress.first_run_id is not None and run.id < progress.first_run_id:
        return None
    return progress


async def reveal_ids(session, progress):
    return set((await session.scalars(select(ChallengeHintReveal.hint_id).where(
        ChallengeHintReveal.progress_id == progress.id,
    ))).all())


def solution_access(progress, hints, used):
    """Only the configured hints count; an empty list never unlocks answers."""
    if expired(progress):
        return 'expired'
    if hints and {hint['id'] for hint in hints}.issubset(used):
        return 'all_hints'
    return None


async def awarded_value(session, run, challenge):
    progress = await lock_progress(session, run, challenge)
    if progress is None:
        # Una corrida anterior a la activación mantiene su política original.
        return challenge.points
    return points_for(progress, len(await reveal_ids(session, progress)))


# El texto se resuelve solo para pistas abiertas; no se incluye oculto en JSON.
FAMILY_HINTS = {
    'base64': ('Comprueba el formato y el alfabeto del mensaje; Base64 no utiliza una clave.',
               'Decodifica una sola capa y conserva el resultado como UTF-8.',
               'Puedes usar base64 -d sobre message.txt. Entrega el texto, no su representación codificada.'),
    'xor': ('Busca los bytes conocidos del prefijo CTF: antes de adivinar el texto completo.',
            'La operación XOR es reversible: cifrado XOR texto conocido revela la clave.',
            'Obtén la clave de un byte con el primer carácter C; úsala sobre todos los bytes y retira el prefijo CTF:.'),
    'rsa': ('El módulo es deliberadamente pequeño: busca sus dos factores primos.',
            'Con p y q calcula phi=(p-1)*(q-1) y el inverso modular de e.',
            'Calcula d=pow(e,-1,phi) y m=pow(c,d,n). La respuesta es m como entero decimal.'),
    'hex_xor': ('Separa la codificación hexadecimal de la operación criptográfica.',
                'Convierte el hexadecimal a bytes y localiza la clave indicada en el expediente.',
                'Aplica XOR byte a byte con key y decodifica el resultado como UTF-8.'),
    'tree': ('El archivo objetivo está descrito por una ruta; otros archivos son señuelos.',
             'Revisa la estructura de la exportación y busca la ruta completa, no solo un nombre repetido.',
             'Abre el registro de la ruta objetivo y entrega su campo evidence, sin comillas ni campos adicionales.'),
    'logs': ('Una autenticación exitosa por sí sola no basta para identificar el incidente.',
             'Combina las tres condiciones: result=success, role=admin y mfa=bypassed.',
             'Filtra los registros que cumplen todas las condiciones y entrega únicamente session.'),
    'services': ('Distingue puertos del cliente de servicios que están escuchando.',
                 'Busca el proceso sshd con protocolo TCP y estado LISTEN.',
                 'Entrega su puerto en decimal. No deduzcas 22 por defecto: el registro puede usar otro puerto.'),
    'join': ('Busca una clave de correlación compartida entre las fuentes.',
             'Relaciona request entre la exportación HTTP y la transferencia de red.',
             'La misma solicitud debe ser POST /admin/export con status=200 y destino 203.0.113.77; entrega su request.'),
    'lateral': ('Los nombres parecidos de equipo no identifican por sí solos una sesión.',
                'Relaciona LogonId entre los eventos 4624 y 7045.',
                'Exige LogonType=3, origen WS-A, destino WS-B y servicio update-agent. Entrega el LogonId común.'),
    'dns_chunks': ('El orden visible del archivo no es necesariamente el orden del mensaje.',
                   'Selecciona las consultas del dominio de transferencia y ordena por seq.',
                   'Concatena data, decodifica Base64 una sola vez y entrega el texto reconstruido.'),
    'chunks': ('Los fragmentos tienen un índice que permite recuperar el orden correcto.',
               'Ordena por seq antes de concatenar el campo data.',
               'Decodifica Base64 sobre la cadena concatenada, no sobre cada fragmento por separado.'),
    'metadata': ('La evidencia puede estar en los metadatos del PNG, no en lo que muestra la imagen.',
                 'Busca los chunks tEXt; contienen pares clave/valor separados por un byte nulo.',
                 'Localiza Case-ID y entrega solo su valor.'),
    'pcap': ('La captura contiene evidencia en un datagrama UDP del laboratorio.',
             'Filtra el puerto UDP 9000 y examina su carga útil.',
             'Busca evidence= dentro del payload y entrega el texto que sigue.'),
    'memory': ('La muestra usa caracteres de dos bytes; una búsqueda ASCII puede omitirlos.',
               'Busca cadenas UTF-16LE y localiza CASE_ACTIVE=.',
               'Entrega el valor posterior al marcador y anterior al terminador nulo.'),
    'integrity': ('El manifiesto representa la adquisición original; el archivo actual puede haber cambiado.',
                  'Calcula SHA-256 de los bytes de cada artefacto y compara con el digest esperado.',
                  'Identifica el único desacuerdo. Conserva nombres y hashes de ambas versiones para justificarlo.'),
    'tutorial': ('Un hash depende de los bytes exactos, incluidos los saltos de línea.',
                 'Calcula SHA-256 directamente sobre evidence.txt, sin copiarlo a otro editor.',
                 'Usa sha256sum evidence.txt y entrega únicamente los 64 caracteres hexadecimales del digest.'),
    'dns': ('Sigue los registros como una cadena, no elijas el primer TXT visible.',
            'Localiza el CNAME de portal.training.example y resuelve su nombre de destino.',
            'Lee el TXT del destino y entrega el valor de case.'),
    'stack': ('La muestra describe una pila simulada, no requiere ejecutar un binario.',
              'Resta la dirección del buffer a la posición de return_address para obtener el desplazamiento.',
              'Combina desplazamiento decimal y dirección win hexadecimal con un signo de dos puntos.'),
    'strings': ('La muestra contiene cadenas ASCII entre datos binarios.',
                'Busca el marcador ACTIVE_EVIDENCE= y evita incluir otros señuelos.',
                'Entrega los caracteres posteriores al marcador hasta el primer byte nulo.'),
    'validator': ('Invierte las operaciones del validador en el orden contrario.',
                  'Primero resta KEY módulo 256 a cada elemento de TARGET.',
                  'Invierte el orden de los bytes recuperados y decodifícalos como texto.'),
    'stego': ('La información está en los bits menos significativos de los píxeles.',
              'Lee RGB en orden de filas y agrupa ocho bits de mayor a menor.',
              'Busca el prefijo CTF: en los bytes reconstruidos y termina en el byte nulo.'),
    'robots': ('robots.txt comunica rutas a rastreadores; no aplica autorización HTTP.',
               'Sigue la ruta Disallow y revisa sus archivos o índices.',
               'Abre la evidencia de esa ruta; en una copia local busca el campo evidence.'),
    'auth': ('Compara el comportamiento esperado con la condición booleana de autenticación.',
             'Una condición OR acepta la solicitud si cualquiera de sus partes resulta verdadera.',
             'Comprueba si el rol controlado por el cliente permite entrar aunque password_ok sea falso.'),
    'sql': ('Localiza una condición que transforme el filtro de contraseña en una expresión siempre verdadera.',
            'Revisa precedencia y agrupación del operador OR.',
            'Selecciona la consulta que evita validar la contraseña y entrega su request_id.'),
    'upload': ('El MIME declarado puede diferir del contenido real del archivo.',
               'Una imagen PNG debe comenzar por la firma hexadecimal 89504e470d0a1a0a.',
               'Busca una subida aceptada por MIME cuya firma no coincida; entrega su id.'),
    'http': ('Las cabeceras pueden contener evidencia aunque el cuerpo parezca vacío.',
             'Localiza X-Evidence-Base64; el nombre indica su codificación.',
             'Decodifica su valor como Base64 y entrega el texto UTF-8 resultante.'),
    'idor': ('Conocer un identificador no equivale a tener autorización sobre el objeto.',
             'Correlaciona el solicitante y el propietario de cada objeto, excluyendo administradores.',
             'Busca una respuesta 200 donde user difiere de owner y documenta qué control faltó.'),
    'windows': ('Combina las propiedades del inventario en vez de elegir por nombre de equipo.',
                'Busca sistema Windows, DomainJoined=true y BitLocker=false simultáneamente.',
                'Entrega ComputerName del único equipo que cumple esas tres condiciones.'),
    'process': ('El nombre del servicio no revela por sí solo qué ejecutable está activo.',
                'Relaciona servicios y procesos por PID.',
                'Busca un servicio Running cuyo proceso ejecute C:\\Users\\Public\\update.exe y entrega el nombre del servicio.'),
}


def _default_hints_for(run, challenge):
    from .guided_hints import hints_for as guided_hints
    guided = guided_hints(run, challenge)
    if guided is not None and run.workspace_strategy not in ('offline_case', 'dfir_case'):
        return guided
    if challenge.code == 'DFIR-01':
        texts = ('Adquiere las fuentes y verifica los hashes antes de correlacionar; una IP o un volumen aislado no basta.',
                 'Calcula los desfases constantes de auth y HTTP con ambas balizas; conviértelos a UTC real.',
                 'Une session entre auth y HTTP, y request entre HTTP y red. Exige MFA bypassed, exportación 200 >500000 bytes, destino 203.0.113.77 y ventana menor de 60 segundos.')
    elif run.workspace_strategy == 'ssh_password_lab':
        texts = ('El objetivo es el servicio de práctica en 192.168.146.137:2222, desde Kali; no uses las cuentas del sistema.',
                 'La cuenta temporal es ctf seguida del identificador de corrida. El diccionario autorizado contiene 12 candidatos.',
                 f'Prueba el diccionario con Hydra sobre SSH, un hilo (-t 1), puerto 2222 y usuario ctf{run.id}; después entra por SSH y usa help para ver cómo leer la evidencia.')
    elif run.workspace_strategy == 'http_password_lab':
        texts = ('Observa el código 401 y la cabecera WWW-Authenticate: el servicio usa HTTP Basic.',
                 'Utiliza la cuenta temporal de esta corrida y únicamente el diccionario autorizado; una respuesta 200 indica acceso.',
                 'Hydra admite el módulo http-get sobre el recurso protegido. Tras encontrar la contraseña, curl --user permite comprobarla sin guardarla en la orden.')
    elif run.workspace_strategy == 'http_files_lab':
        texts = ('Comienza en los recursos públicos de la URL de tu corrida y distingue pistas de controles de acceso.',
                 'robots.txt puede revelar directorios que el administrador no quería indexar. Visita la ruta mencionada.',
                 'Inspecciona los respaldos y sus referencias; comprueba nombres, versiones y cualquier manifiesto antes de elegir evidencia.')
    elif challenge.code == 'ESC-01-RECON':
        texts = ('Trabaja desde Kali hacia la víctima .137; tu objetivo es reconocer servicios, no iniciar sesión en la víctima.',
                 'Compara los servicios TCP 22 y 18081 e identifica cuál habla HTTP.',
                 'Consulta /evidence en el servicio HTTP de práctica y registra la evidencia de esta corrida.')
    elif challenge.code == 'LAB-01':
        texts = ('La terminal asignada abre la máquina víctima; confirma en qué sistema estás trabajando.',
                 'La evidencia didáctica se coloca bajo /opt/ctf.',
                 'Consulta /opt/ctf/flag.txt, copia el valor completo FLAG{...} y envíalo antes del plazo.')
    else:
        family = CATALOG.get(challenge.code, ('', '', ''))[1]
        texts = FAMILY_HINTS.get(family, ('Revisa el objetivo y distingue las fuentes relevantes de los señuelos.',
                                        'Relaciona los campos o transformaciones compartidos entre las evidencias.',
                                        'Verifica el formato de respuesta y conserva los pasos que justifican tu resultado.'))
    return [{'id': index, 'title': title, 'content': content} for index, (title, content) in enumerate(
        zip(('Dónde empezar', 'Relaciona las pistas', 'Cómo comprobarlo'), texts), start=1)]


def hints_for(run, challenge, progress=None):
    if progress is None:
        return _default_hints_for(run, challenge)
    policy = policy_for_progress(progress, run, challenge)
    return [{'id': index, 'title': hint['title'].replace('{{RUN_ID}}', str(run.id)),
             'content': hint['content'].replace('{{RUN_ID}}', str(run.id)),
             'penalty_percent': hint['penalty_percent']} for index, hint in enumerate(policy['hints'], start=1)]


async def metadata(session, run, challenge, progress):
    used = await reveal_ids(session, progress)
    completion = await session.scalar(select(ChallengeCompletion).where(
        ChallengeCompletion.user_id == run.user_id, ChallengeCompletion.challenge_id == challenge.id))
    hints = hints_for(run, challenge, progress)
    access = solution_access(progress, hints, used)
    result = {'base_points': progress.base_points, 'expired_points_percent': expired_percent(progress), 'hint_count': len(hints),
              'duration_minutes': policy_for_progress(progress, run, challenge)['duration_minutes'],
              'timer_enabled': policy_for_progress(progress, run, challenge).get('timer_enabled', True),
              'solution_available': access is not None, 'solution_reason': access,
              'available_points': completion.awarded_points if completion is not None else points_for(progress, len(used)),
              'deadline': utc(progress.deadline).isoformat(), 'expired': expired(progress), 'hints_used': len(used),
              'hints': [{'id': hint['id'], 'title': hint['title'], 'unlocked': hint['id'] in used,
                         'penalty_percent': hint['penalty_percent'],
                         **({'content': hint['content']} if hint['id'] in used else {})} for hint in hints],
              'solution_revealed': progress.solution_revealed_at is not None, 'completed': completion is not None}
    if completion is not None:
        result['awarded_points'] = completion.awarded_points
    return result


def solution_for(run, challenge):
    """Generar el material solo después de que el endpoint autorice el plazo."""
    if run.workspace_strategy == 'external_web_lab':
        return {'steps': [
            'Desde Kali, reconoce los servicios HTTP de la víctima dentro del rango autorizado.',
            'Consulta robots.txt, sigue el manifiesto y correlaciona las cuentas con su último estado para identificar al editor activo.',
            'Descarga el diccionario indicado por el manifiesto y prueba el formulario /login con Hydra, un solo hilo y esa cuenta.',
            'Entra al centro de mando, publica un comunicado y copia la flag que muestra el portal.',
            'Registra la flag en Cociber CTF o completa el repaso asistido con el puntaje indicado.',
        ], 'answer': None,
            'note': 'El portal local es compartido. La flag pertenece a esa instalación y solo se muestra después de publicar.'}
    if run.workspace_strategy == 'vm_logic_lab':
        from . import vm_logic
        if hasattr(vm_logic, 'solution_for'):
            return vm_logic.solution_for(run, challenge.code)
        _, expected = vm_logic.case_for(run, challenge.code)
        return {'steps': [hint['content'] for hint in hints_for(run, challenge)],
                'answer': json.dumps(expected, ensure_ascii=False, sort_keys=True, indent=2)}
    if run.workspace_strategy == 'offline_case':
        from . import offline_runtime
        _, expected = offline_runtime.case_for(run, challenge.code)
        return {'steps': [hint['content'] for hint in hints_for(run, challenge)], 'answer': str(expected)}
    if run.workspace_strategy == 'dfir_case':
        from . import dfir_runtime
        _, expected = dfir_runtime.case_for(run)
        return {'steps': [hint['content'] for hint in hints_for(run, challenge)],
                'answer': json.dumps(expected, ensure_ascii=False, sort_keys=True, indent=2)}
    if run.workspace_strategy == 'ssh_password_lab':
        from . import ssh_practice
        return {'steps': ssh_practice.instructions(run)['commands'],
                'answer': json.dumps({'username': f'ctf{run.id}', 'password': ssh_practice.password_for(run),
                                     'flag': ssh_practice.flag_for(run)}, ensure_ascii=False),
                'note': 'Usa la cuenta mientras la corrida siga activa. Mostrar la explicación no amplía el plazo ni reactiva una cuenta caducada.'}
    if run.workspace_strategy in ('http_password_lab', 'http_files_lab'):
        from . import http_practice
        if run.workspace_strategy == 'http_password_lab':
            base = http_practice.instructions(run)['base_url']
            steps = ['Crea un diccionario con los 12 candidatos de práctica autorizados.',
                     f'Ejecuta hydra -l ctf{run.id} -P diccionario.txt -t 1 -f -s 18082 192.168.146.137 http-get /practice/{run.id}/private/flag.txt',
                     f'Comprueba la contraseña mediante curl --user ctf{run.id} {base}private/flag.txt.']
            answer = {'username': f'ctf{run.id}', 'password': http_practice.password_for(run),
                      'flag': http_practice.flag_for(run)}
        else:
            _, answer = http_practice.case_for(run)
            steps = ['Consulta robots.txt de la corrida y sigue la ruta de respaldos.',
                     'Lee el manifiesto y compara versiones y SHA-256; descarta los respaldos que no coinciden.',
                     'Adquiere los fragmentos de la versión vigente, reconstruye el valor con XOR y documenta respaldo, release y evidencia.']
        return {'steps': steps, 'answer': json.dumps(answer, ensure_ascii=False, sort_keys=True, indent=2),
                'note': 'Los recursos de la corrida pueden estar caducados; la explicación no los reactiva.'}
    if challenge.code == 'ESC-01-RECON':
        steps = ['Desde Kali, identifica los servicios de 192.168.146.137 en los puertos 22 y 18081.',
                 'Solicita curl http://192.168.146.137:18081/evidence durante una corrida activa.',
                 'Copia la flag dinámica completa y envíala en la plataforma.']
    else:
        steps = ['Abre la conexión SSH de la VM asignada y localiza /opt/ctf.',
                 'Lee cat /opt/ctf/flag.txt y copia el valor completo FLAG{...}.',
                 'Durante una corrida activa, envía el valor para validar tu evidencia.']
    return {'steps': steps, 'answer': None,
            'note': 'La respuesta original no está disponible de forma verificable para esta corrida. Puedes seguir el procedimiento y registrar el repaso asistido con el puntaje disponible indicado.'}


async def solution_for_run(session, run, challenge, progress=None):
    """El endpoint llama este proveedor únicamente tras autorizar el plazo."""
    solution = solution_for(run, challenge)
    if run.workspace_strategy == 'shared_lab_vm':
        from .dynamic_flags import restored_run_answers
        answers = await restored_run_answers(session, run)
        if answers:
            solution['answer'] = '\n'.join(answers)
            solution['note'] = 'Respuesta original de esta corrida, comprobada contra su hash. Mostrarla no reactiva la VM ni cambia puntos ya registrados.'
    if progress is not None:
        configured = policy_for_progress(progress, run, challenge).get('solution_text')
        if configured:
            solution['steps'] = [line.strip().replace('{{RUN_ID}}', str(run.id)) for line in configured.splitlines() if line.strip()]
            solution['note'] = 'Explicación configurada por el instructor; la respuesta dinámica, cuando existe, corresponde a esta corrida.'
    return solution
