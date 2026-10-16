"""Prepara dos ejercicios HTTP en LNX-VICT sin cuentas del sistema ni sudo."""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import shlex
import stat
import time
import random
import paramiko
from ..core import submission_fingerprint
from .ssh_practice import connection, WORDS

HOST = '192.168.146.137'
PORT = 18082
PASSWORD_CODE = 'ESC-06-WEBAUTH'
FILES_CODE = 'ESC-07-EXPOSED'
CODES = (PASSWORD_CODE, FILES_CODE)
PASSWORD_STRATEGY = 'http_password_lab'
FILES_STRATEGY = 'http_files_lab'
STRATEGIES = (PASSWORD_STRATEGY, FILES_STRATEGY)
BACKUP_FILE = 'audit-backup.txt'
VM_LOGIC_STRATEGY = 'vm_logic_lab'
SERVER_VERSION = '3'


def _strategy(run):
    value = getattr(run, 'workspace_strategy', None)
    if value not in STRATEGIES:
        raise ValueError('Estrategia HTTP de práctica inválida')
    return value


def _run_id(value):
    if isinstance(value, bool):
        raise ValueError('Corrida HTTP inválida')
    number = int(value)
    if str(number) != str(value) or not 1 <= number <= 999999999999:
        raise ValueError('Corrida HTTP inválida')
    return number


def password_for(run):
    if _strategy(run) != PASSWORD_STRATEGY:
        raise ValueError('Este ejercicio no utiliza contraseñas')
    index = int(submission_fingerprint(f'http-practice:password:{run.user_id}:{run.id}')[:8], 16) % len(WORDS)
    return WORDS[index]


def flag_for(run):
    strategy = _strategy(run)
    kind = 'password' if strategy == PASSWORD_STRATEGY else 'files'
    return 'FLAG{http_' + kind + '_' + submission_fingerprint(f'http-practice:{kind}:flag:{run.user_id}:{run.id}') + '}'


def _command(client, command):
    _, out, _ = client.exec_command(command, timeout=20)
    out.read()
    if out.channel.recv_exit_status() != 0:
        raise RuntimeError('La VM no pudo preparar el servicio HTTP de práctica')


def provision(run_id, strategy, password, flag, expires, case=None):
    run_id = _run_id(run_id)
    if strategy not in (*STRATEGIES, VM_LOGIC_STRATEGY):
        raise ValueError('Estrategia HTTP de práctica inválida')
    with connection() as client, client.open_sftp() as sftp:
        directory = sftp.normalize('.') + '/.ctf-http-practice'
        try:
            sftp.mkdir(directory, 0o700)
        except OSError:
            if not stat.S_ISDIR(sftp.lstat(directory).st_mode):
                raise RuntimeError('Directorio HTTP de práctica inválido')
        sftp.chmod(directory, 0o700)
        script = Path(__file__).parents[1] / 'infrastructure/injection/scripts/linux/ctf-http-practice.py'
        remote = directory + '/server.py'
        source = script.read_bytes()
        try:
            with sftp.open(remote, 'rb') as old:
                source_changed = old.read() != source
        except FileNotFoundError:
            source_changed = False
        # Reemplazo atómico: dos corridas concurrentes no ven código incompleto.
        script_temp = remote + '.' + str(run_id) + '.tmp'
        with sftp.open(script_temp, 'w') as file:
            file.write(source)
        sftp.chmod(script_temp, 0o600)
        sftp.posix_rename(script_temp, remote)
        config = {'strategy': strategy, 'flag': flag, 'expires_at': expires}
        if strategy == PASSWORD_STRATEGY:
            config['password_sha256'] = hashlib.sha256(password.encode('utf-8')).hexdigest()
        elif case is not None:
            config['case'] = case
        else:
            raise ValueError('La práctica requiere sus evidencias remotas')
        path = directory + '/ctf' + str(run_id) + '.json'
        temp = path + '.tmp'
        with sftp.open(temp, 'w') as file:
            file.write(json.dumps(config))
        sftp.chmod(temp, 0o600)
        sftp.posix_rename(temp, path)
        if source_changed:
            # Recargar exclusivamente el proceso propio de este directorio. Los
            # registros por corrida sobreviven y ninguna cuenta del host cambia.
            restart = ("import os,pathlib,signal,time; "
                       f"expected=[b'python3',{remote.encode()!r},b'--directory',{directory.encode()!r}]; "
                       "pids=[]; "
                       "\nfor p in pathlib.Path('/proc').glob('[0-9]*'):"
                       "\n try:"
                       "\n  if p.stat().st_uid==os.getuid() and (p/'cmdline').read_bytes().rstrip(b'\\0').split(b'\\0')==expected: pids.append(int(p.name))"
                       "\n except (OSError,ValueError): pass"
                       "\nfor pid in pids:"
                       "\n try: os.kill(pid,signal.SIGTERM)"
                       "\n except ProcessLookupError: pass"
                       "\nif pids: time.sleep(0.5)")
            _command(client, 'python3 -c ' + shlex.quote(restart))
        command = ('nohup flock -n ' + shlex.quote(directory + '/server.lock') + ' python3 '
                   + shlex.quote(remote) + ' --directory ' + shlex.quote(directory)
                   + ' </dev/null >' + shlex.quote(directory + '/server.log') + ' 2>&1 &')
        _command(client, command)
        for _ in range(40):
            try:
                channel = client.get_transport().open_channel(
                    'direct-tcpip', (HOST, PORT), ('127.0.0.1', 0), timeout=2)
                channel.settimeout(3)
                resource = f'/__ctf-health/{run_id}'
                channel.sendall(f'GET {resource} HTTP/1.0\r\nHost: {HOST}\r\n\r\n'.encode())
                response = b''
                while b'\r\n\r\n' not in response and len(response) < 8192:
                    chunk = channel.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                channel.close()
                if (b'X-CTF-Practice-Version: ' + SERVER_VERSION.encode()) in response and response.startswith(b'HTTP/1.0 200'):
                    return
                time.sleep(0.5)
            except (OSError, paramiko.SSHException):
                time.sleep(0.5)
        raise RuntimeError('El puerto 18082 no está disponible en LNX-VICT')


def remove(run_id):
    run_id = _run_id(run_id)
    with connection() as client, client.open_sftp() as sftp:
        path = sftp.normalize('.') + '/.ctf-http-practice/ctf' + str(run_id) + '.json'
        try:
            sftp.remove(path)
        except FileNotFoundError:
            pass


async def prepare(run):
    strategy = _strategy(run)
    password = password_for(run) if strategy == PASSWORD_STRATEGY else None
    try:
        case = case_for(run)[0] if strategy == FILES_STRATEGY else None
        await asyncio.to_thread(provision, run.id, strategy, password, flag_for(run), run.expires_at.timestamp(), case)
    except Exception:
        try:
            await asyncio.to_thread(remove, run.id)
        except Exception:
            pass
        raise


async def cleanup(run):
    await asyncio.to_thread(remove, run.id)


def instructions(run):
    strategy = _strategy(run)
    run_id = _run_id(run.id)
    base = f'http://{HOST}:{PORT}/practice/{run_id}/'
    if strategy == PASSWORD_STRATEGY:
        username = f'ctf{run_id}'
        return {
            'target': f'{HOST}:{PORT}', 'base_url': base, 'username': username, 'wordlist': list(WORDS),
            'objective': 'Adivina la contraseña de la cuenta de práctica HTTP Basic y recupera la flag privada.',
            'commands': [],
            'note': 'HTTP Basic real de práctica. Explora la URL privada de esta cuenta (private/flag.txt) y reconoce la respuesta 401 antes de probar los doce candidatos desde Kali. El acceso se invalida al cerrar o caducar la corrida.',
        }
    return {
        'target': f'{HOST}:{PORT}', 'base_url': base,
        'objective': case_for(run)[0]['objective'], 'commands': [],
        'answer_fields': case_for(run)[0]['answer_fields'],
        'note': 'Explora la URL inicial desde Kali. Correlaciona el manifiesto con los respaldos y reconstruye la evidencia. No se entrega una flag directamente en un archivo.',
    }


def case_for(run):
    """Respaldo por corrida: descubrimiento, integridad y reconstrucción."""
    if _strategy(run) != FILES_STRATEGY:
        raise ValueError('Solo el ejercicio de respaldos tiene un caso de análisis')
    seed = submission_fingerprint(f'http-practice:files:v2:{run.user_id}:{run.id}')
    rng = random.Random(seed)
    evidence = f'{rng.getrandbits(96):024x}'
    directory = 'archive-' + f'{rng.getrandbits(32):08x}'
    release = 'rel-' + str(rng.randrange(1000, 9999))
    key = rng.randrange(1, 256)
    encoded = bytes(byte ^ key for byte in evidence.encode()).hex()
    fragments = [{'seq': index, 'hex': encoded[index * 8:index * 8 + 8]} for index in range(len(encoded) // 8)]
    rng.shuffle(fragments)
    selected = 'backup-' + f'{rng.getrandbits(32):08x}' + '.json'
    documents = {selected: json.dumps({'release': release, 'fragments': fragments}, sort_keys=True).encode()}
    for index in range(2):
        name = 'backup-' + f'{rng.getrandbits(32):08x}' + '.json'
        documents[name] = json.dumps({'release': release if index else 'rel-obsolete',
                                     'fragments': [{'seq': 0, 'hex': '00000000'}]}, sort_keys=True).encode()
    names = list(documents)
    rng.shuffle(names)
    files = {}

    def add(path, content, content_type='text/plain; charset=utf-8'):
        data = content if isinstance(content, bytes) else content.encode()
        files[path] = {'body': base64.b64encode(data).decode(), 'content_type': content_type}

    base = f'/practice/{int(run.id)}/'
    add('index.html', '<!doctype html><html lang="es"><title>Portal de respaldos</title>'
        '<h1>Portal de respaldos</h1><p>Las políticas de rastreo del sitio están disponibles en '
        '<a href="robots.txt">robots.txt</a>.</p><p>Solo un respaldo coincide con la versión e integridad vigentes.</p></html>', 'text/html; charset=utf-8')
    add('robots.txt', f'User-agent: *\nDisallow: {base}{directory}/\n')
    add(directory + '/index.html', '<!doctype html><html lang="es"><h1>Archivo de versiones</h1>'
        '<a href="manifest.json">manifest.json</a><ul>' + ''.join(f'<li><a href="{name}">{name}</a></li>' for name in names) + '</ul></html>', 'text/html; charset=utf-8')
    manifest = {'current_release': release, 'sha256': hashlib.sha256(documents[selected]).hexdigest(),
                'encoding': 'Ordena fragments por seq, concatena hex, convierte a bytes y aplica XOR con key.', 'key': key}
    add(directory + '/manifest.json', json.dumps(manifest), 'application/json; charset=utf-8')
    for name, data in documents.items():
        add(directory + '/' + name, data, 'application/json; charset=utf-8')
    return {'code': FILES_CODE, 'files': files, 'web_data': {},
            'objective': 'Descubre los respaldos expuestos. Identifica la versión vigente por su release y SHA-256, descarta señuelos y reconstruye la evidencia de sus fragmentos.',
            'answer_fields': [{'key': 'backup', 'label': 'Nombre del respaldo correcto'},
                              {'key': 'release', 'label': 'Versión vigente (release)'},
                              {'key': 'evidence', 'label': 'Evidencia reconstruida'}]}, {'backup': selected, 'release': release, 'evidence': evidence}
