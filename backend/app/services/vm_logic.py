"""Casos de lógica con adquisición y aplicación HTTP reales en LNX-VICT."""
import asyncio
import base64
import hashlib
import hmac
import json
import random

from ..core import submission_fingerprint
from ..domain.challenges import dfir, offline
from . import http_practice

STRATEGY = 'vm_logic_lab'
CODES = ('WEB-02', 'WEB-06', 'FOR-05', 'DFIR-01')
EXPECTED_SCENARIOS = {code: 'VM-LOGIC-' + code for code in CODES}


def _field(key, label, placeholder=None):
    return {'key': key, 'label': label, **({'placeholder': placeholder} if placeholder else {})}


def case_for(run, code):
    if code not in CODES:
        raise ValueError('Caso VM desconocido')
    seed = submission_fingerprint(f'vm-logic:case:v1:{code}:{run.user_id}:{run.id}')
    rng = random.Random(seed)
    token = f'{rng.getrandbits(96):024x}'
    files, web_data = {}, {}

    def add(path, content, content_type='text/plain; charset=utf-8'):
        data = content if isinstance(content, bytes) else content.encode('utf-8')
        files[path] = {'body': base64.b64encode(data).decode(), 'content_type': content_type}

    def js(path, data):
        add(path, json.dumps(data, ensure_ascii=False, indent=2), 'application/json; charset=utf-8')

    if code == 'WEB-02':
        role = rng.choice(('support', 'auditor', 'reviewer'))
        session = 's-' + token
        user = 'operador-' + str(rng.randrange(100, 999))
        secret = f'{rng.getrandbits(192):048x}'
        web_data = {'kind': 'auth', 'role': role, 'user': user, 'session': session,
                    'password_sha256': hashlib.sha256(secret.encode()).hexdigest()}
        add('index.html', '<!doctype html><html lang="es"><title>Portal de soporte</title>'
            '<h1>Portal de soporte</h1><p>Cliente de referencia: <a href="assets/login.js">login.js</a>.</p>'
            '<p>POST login admite JSON con user, password y role. No hay cuentas externas.</p>'
            '<p>Investiga por qué el formulario autoriza una sesión aunque la contraseña sea incorrecta.</p></html>', 'text/html; charset=utf-8')
        add('assets/login.js', '// Contrato del portal de práctica. El servidor reproduce esta condición.\n'
            f'const account = {json.dumps(user)};\n'
            'function allowed(password_ok, role) {\n'
            f'  return password_ok || role === {json.dumps(role)};\n'
            '}\n// Roles históricos: admin y reader no tienen excepción.\n'
            '// Envía {user: account, password: texto, role: texto} al recurso login.\n', 'application/javascript; charset=utf-8')
        objective = 'Investiga el cliente público, demuestra el fallo lógico de autenticación en el servicio y recupera la sesión autorizada con una contraseña incorrecta.'
        fields = [_field('session', 'Sesión obtenida'), _field('role', 'Rol que permitió el acceso')]
        expected = {'session': session, 'role': role}
    elif code == 'WEB-06':
        own_id = rng.randrange(1000, 3000)
        foreign_id = own_id + rng.randrange(17, 83)
        decoy_id = foreign_id + rng.randrange(11, 39)
        owner = 'finanzas-' + str(rng.randrange(100, 999))
        user = 'analista-' + str(rng.randrange(100, 999))
        web_data = {'kind': 'idor', 'user': user, 'own_id': own_id,
                    'objects': {
                        str(own_id): {'id': own_id, 'owner': user, 'title': 'Índice de revisión',
                                      'related_document': foreign_id, 'review_case': 'INC-' + token[:8]},
                        str(foreign_id): {'id': foreign_id, 'owner': owner, 'title': 'Informe relacionado',
                                         'review_case': 'INC-' + token[:8], 'evidence': token},
                        str(decoy_id): {'id': decoy_id, 'owner': 'archivo', 'title': 'Informe histórico',
                                       'review_case': 'CLOSED-2025', 'evidence': 'obsolete-' + token[:8]},
                    }}
        add('index.html', '<!doctype html><html lang="es"><title>Documentos de auditoría</title>'
            '<h1>Documentos de auditoría</h1><p>La sesión de práctica ya está autenticada.</p>'
            '<p><a href="api/profile">Perfil actual</a> · <a href="api/documents">Mis documentos</a></p>'
            '<p>La API permite consultar api/documents/ID. Un vínculo de revisión debe respetar su propietario.</p></html>', 'text/html; charset=utf-8')
        objective = 'Parte del perfil y sus documentos. Sigue la referencia del caso y demuestra que la API entrega un documento de otro propietario. Identifica objeto, propietario y evidencia del mismo caso.'
        fields = [_field('object', 'ID del objeto ajeno'), _field('owner', 'Propietario real'), _field('evidence', 'Evidencia del caso')]
        expected = {'object': str(foreign_id), 'owner': owner, 'evidence': token}
    elif code == 'FOR-05':
        original, changed = offline.build_case(code, seed)
        acquisition = json.loads(base64.b64decode(original['files']['acquisition.json']))
        actual = {name: base64.b64decode(value) for name, value in original['files'].items()
                  if name.startswith('artifact-')}
        listing = []
        for name, data in actual.items():
            add('artifacts/' + name, data)
            listing.append({'file': name, 'path': 'artifacts/' + name, 'sha256_at_acquisition': acquisition[name]})
        js('acquisition.json', {'case': 'ACQ-' + token[:8], 'algorithm': 'SHA-256', 'artifacts': listing})
        add('index.html', '<!doctype html><html lang="es"><title>Adquisición forense</title>'
            '<h1>Adquisición forense</h1><p>Preserva los bytes que devuelve la víctima.</p>'
            '<p><a href="acquisition.json">Manifiesto de adquisición</a></p>'
            '<p>El manifiesto corresponde a la adquisición inicial. Un artefacto cambió después.</p></html>', 'text/html; charset=utf-8')
        objective = 'Adquiere el manifiesto y sus ocho artefactos desde LNX-VICT. Calcula SHA-256 en Kali y determina el archivo alterado, su hash de adquisición y el observado. No basta con leer el manifiesto.'
        fields = [_field('file', 'Archivo alterado'), _field('expected_sha256', 'SHA-256 de adquisición'), _field('observed_sha256', 'SHA-256 observado')]
        expected = {'file': changed, 'expected_sha256': acquisition[changed],
                    'observed_sha256': hashlib.sha256(actual[changed]).hexdigest()}
    else:
        source, expected = dfir.build_case(seed)
        for name, content in source['files'].items():
            add(name, content, 'application/json; charset=utf-8')
        js('calibration.json', {'clock_notes': source['clock_notes'], 'calibration': source['calibration']})
        manifest = {name: hashlib.sha256(base64.b64decode(value['body'])).hexdigest() for name, value in files.items()}
        js('manifest.json', {'case': 'DFIR-' + token[:8], 'sha256': manifest})
        add('index.html', '<!doctype html><html lang="es"><title>Expediente DFIR</title>'
            '<h1>Expediente DFIR</h1><p>Adquiere y verifica las fuentes antes de analizarlas.</p>'
            '<p><a href="manifest.json">Manifiesto</a> · <a href="auth.json">Auth</a> · '
            '<a href="http.json">HTTP</a> · <a href="network.json">Red</a> · '
            '<a href="calibration.json">Calibración</a></p></html>', 'text/html; charset=utf-8')
        objective = source['brief'] + ' Adquiere las cuatro fuentes desde la víctima y verifica sus hashes. Los relojes Auth y HTTP requieren calibración.'
        fields = [_field('session', 'Sesión'), _field('user', 'Usuario'), _field('request', 'Solicitud HTTP'),
                  _field('destination', 'IP de destino'), _field('auth_utc', 'Autenticación real en UTC', '2026-09-21T14:00:00+00:00')]
    return {'code': code, 'objective': objective, 'files': files, 'web_data': web_data,
            'answer_fields': fields}, expected


def flag_for(run):
    return 'FLAG{vm_logic_' + submission_fingerprint(f'vm-logic:flag:v1:{run.challenge_id}:{run.user_id}:{run.id}') + '}'


def metadata(run, code):
    bundle, _ = case_for(run, code)
    return {'target': f'{http_practice.HOST}:{http_practice.PORT}',
            'base_url': f'http://{http_practice.HOST}:{http_practice.PORT}/practice/{int(run.id)}/',
            'objective': bundle['objective'], 'answer_fields': bundle['answer_fields'],
            'note': 'Trabaja desde la terminal Kali. Explora el servicio y conserva tus evidencias en una carpeta de la corrida. Las fuentes remotas dejan de estar disponibles al cerrar o caducar.'}


def matches_answer(code, expected, supplied):
    if set(supplied) != set(expected) or any(not isinstance(value, str) for value in supplied.values()):
        return False
    if code == 'DFIR-01':
        return dfir.matches_answer(expected, supplied)
    return all(hmac.compare_digest(str(value).strip().casefold().encode(), supplied[key].strip().casefold().encode())
               for key, value in expected.items())


async def prepare(run, code):
    bundle, _ = case_for(run, code)
    try:
        await asyncio.to_thread(http_practice.provision, run.id, STRATEGY, None, flag_for(run),
                                run.expires_at.timestamp(), bundle)
    except Exception:
        try:
            await asyncio.to_thread(http_practice.remove, run.id)
        except Exception:
            pass
        raise


async def cleanup(run):
    await asyncio.to_thread(http_practice.remove, run.id)


def solution_for(run, code):
    """Solo para el endpoint de solución comprada; nunca forma parte del caso."""
    _, expected = case_for(run, code)
    steps = {
        'WEB-02': ['Consulta la página inicial y descarga assets/login.js desde Kali.',
                   'Identifica la cuenta y la excepción de rol en password_ok OR role. Compara un rol sin excepción con el rol admitido.',
                   'Envía POST login con Content-Type application/json, la cuenta indicada, una contraseña incorrecta y el rol de excepción. Recupera session y role de la respuesta autenticada.'],
        'WEB-06': ['Consulta api/profile y api/documents desde la URL de la corrida.',
                   'Abre el documento propio y sigue related_document con api/documents/ID.',
                   'Comprueba que su owner difiere del perfil y que review_case coincide. Presenta id, owner y evidence de ese documento.'],
        'FOR-05': ['Adquiere acquisition.json y los ocho archivos de artifacts/ conservando sus bytes.',
                   'Calcula sha256sum de cada archivo en Kali y compara con sha256_at_acquisition.',
                   'Selecciona la única discrepancia y entrega nombre, hash de adquisición y hash observado.'],
        'DFIR-01': ['Adquiere manifest.json, auth.json, http.json, network.json y calibration.json. Verifica SHA-256 contra el manifiesto.',
                    'Resta reference_utc de auth_clock y http_clock para obtener sus desfases constantes. Descuenta esos valores de cada registro.',
                    'Une Auth y HTTP por session; une HTTP y red por request. Filtra MFA bypassed, exportación exitosa de más de 500000 bytes, destino 203.0.113.77 y menos de 60 segundos desde la autenticación corregida.',
                    'Presenta los cinco campos del único candidato y la autenticación corregida como fecha ISO 8601 con zona UTC.'],
    }[code]
    return {'steps': steps, 'answer': json.dumps(expected, ensure_ascii=False),
            'note': 'Esta reconstrucción corresponde únicamente a la corrida actual.'}
