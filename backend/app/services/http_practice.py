"""Prepara dos ejercicios HTTP en LNX-VICT sin cuentas del sistema ni sudo."""
import asyncio
import hashlib
import json
from pathlib import Path
import shlex
import stat
import time
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


def provision(run_id, strategy, password, flag, expires):
    run_id = _run_id(run_id)
    if strategy not in STRATEGIES:
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
        # Reemplazo atómico: dos corridas concurrentes no ven código incompleto.
        script_temp = remote + '.' + str(run_id) + '.tmp'
        with sftp.open(script_temp, 'w') as file:
            file.write(script.read_bytes())
        sftp.chmod(script_temp, 0o600)
        sftp.posix_rename(script_temp, remote)
        config = {'strategy': strategy, 'flag': flag, 'expires_at': expires}
        if strategy == PASSWORD_STRATEGY:
            config['password_sha256'] = hashlib.sha256(password.encode('utf-8')).hexdigest()
        path = directory + '/ctf' + str(run_id) + '.json'
        temp = path + '.tmp'
        with sftp.open(temp, 'w') as file:
            file.write(json.dumps(config))
        sftp.chmod(temp, 0o600)
        sftp.posix_rename(temp, path)
        command = ('nohup flock -n ' + shlex.quote(directory + '/server.lock') + ' python3 '
                   + shlex.quote(remote) + ' --directory ' + shlex.quote(directory)
                   + ' </dev/null >' + shlex.quote(directory + '/server.log') + ' 2>&1 &')
        _command(client, command)
        for _ in range(40):
            try:
                channel = client.get_transport().open_channel(
                    'direct-tcpip', (HOST, PORT), ('127.0.0.1', 0), timeout=2)
                channel.close()
                return
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
        await asyncio.to_thread(provision, run.id, strategy, password, flag_for(run), run.expires_at.timestamp())
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
        dictionary_file = f'/tmp/ctf-web-passwords-{run_id}.txt'
        dictionary = "printf '%s\\n' " + ' '.join(shlex.quote(word) for word in WORDS) + ' > ' + dictionary_file
        path = f'/practice/{run_id}/private/flag.txt'
        return {
            'target': f'{HOST}:{PORT}', 'base_url': base, 'username': username, 'wordlist': list(WORDS),
            'objective': 'Adivina la contraseña de la cuenta de práctica HTTP Basic y recupera la flag privada.',
            'commands': [dictionary,
                         f'hydra -l {username} -P {dictionary_file} -t 1 -f -s {PORT} {HOST} http-get {path}',
                         f'curl --fail --user {username} {base}private/flag.txt'],
            'note': 'HTTP Basic real de práctica. Usa solamente estos 12 candidatos desde Kali contra el puerto 18082 indicado. El último comando solicita la contraseña encontrada; el acceso se invalida al cerrar o caducar la corrida.',
        }
    return {
        'target': f'{HOST}:{PORT}', 'base_url': base,
        'objective': 'Encuentra un respaldo publicado por error, siguiendo robots.txt y el listado del directorio.',
        'commands': [f'curl --fail {base}robots.txt', f'curl --fail {base}backup/',
                     f'curl --fail {base}backup/{BACKUP_FILE}'],
        'note': 'Descubre la ruta del respaldo en robots.txt, consulta el listado y recupera el archivo publicado. Todas las respuestas son evidencias didácticas de esta corrida; no se publica el sistema de archivos de la VM.',
    }
