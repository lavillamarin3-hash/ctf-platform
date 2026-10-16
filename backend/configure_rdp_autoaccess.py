"""Consultar/desactivar el bloqueo XFCE solo en los dos escritorios del laboratorio.

--check (predeterminado) no escribe preferencias. --apply modifica únicamente
cuatro booleanos por el bus de las sesiones XFCE del propio usuario RDP. No
edita XML, no cambia cuentas/contraseñas y no reinicia ni detiene procesos.
"""
import argparse
import asyncio
from contextlib import contextmanager
import json
import shlex
import sys
from urllib.parse import quote
import paramiko
from app.core import get_settings
from app.guacamole import make_guacamole_admin


LAB_HOSTS = frozenset(('192.168.146.134', '192.168.146.137'))

# Se ejecuta como el mismo usuario de la conexión RDP; no utiliza sudo.
REMOTE_SCRIPT = r'''
import json
import os
from pathlib import Path
import subprocess
import sys

PREFERENCES = (
    ('xfce4-screensaver', '/lock/enabled'),
    ('xfce4-screensaver', '/lock/sleep-activation'),
    ('xfce4-screensaver', '/saver/idle-activation/enabled'),
    ('xfce4-power-manager', '/xfce4-power-manager/lock-screen-suspend-hibernate'),
)

class PreferenceError(RuntimeError):
    pass

def discover_sessions(proc_root='/proc'):
    sessions = {}
    uid = os.geteuid()
    for process in Path(proc_root).iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != uid or process.joinpath('comm').read_text().strip() != 'xfce4-session':
                continue
            environment = {}
            for entry in process.joinpath('environ').read_bytes().split(b'\0'):
                if b'=' not in entry:
                    continue
                key, value = entry.split(b'=', 1)
                if key in (b'DISPLAY', b'DBUS_SESSION_BUS_ADDRESS', b'XAUTHORITY', b'XDG_RUNTIME_DIR'):
                    environment[key.decode('ascii')] = value.decode('utf-8')
            bus = environment.get('DBUS_SESSION_BUS_ADDRESS')
            if bus and environment.get('DISPLAY'):
                sessions.setdefault(bus, environment)
        except (OSError, UnicodeError):
            continue
    return list(sessions.values())

def query(channel, property_name, environment):
    result = subprocess.run(['xfconf-query', '-c', channel, '-p', property_name],
                            env=environment, capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        value = result.stdout.strip().lower()
        if value not in ('true', 'false'):
            raise PreferenceError('bad-value')
        return value == 'true'
    if 'does not exist' in result.stderr:
        return None
    raise PreferenceError('query-failed')

def configure(apply=False, proc_root='/proc'):
    sessions = discover_sessions(proc_root)
    if not sessions:
        raise PreferenceError('no-session')
    reports = []
    for session in sessions:
        environment = dict(os.environ)
        environment.update(session)
        environment['LC_ALL'] = 'C'
        before = {}
        after = {}
        for channel, property_name in PREFERENCES:
            key = channel + ':' + property_name
            value = query(channel, property_name, environment)
            before[key] = value
            if apply and value is not False:
                command = ['xfconf-query', '-c', channel, '-p', property_name, '-s', 'false']
                if value is None:
                    command.extend(['-n', '-t', 'bool'])
                result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    raise PreferenceError('update-failed')
                value = query(channel, property_name, environment)
                if value is not False:
                    raise PreferenceError('verify-failed')
            after[key] = value
        reports.append({'before': before, 'after': after})
    return {'sessions': reports}

if __name__ == '__main__':
    try:
        print(json.dumps(configure(apply='--apply' in sys.argv[1:])))
    except PreferenceError as exc:
        print(json.dumps({'error': str(exc)}))
        raise SystemExit(1)
'''


class AutoAccessError(RuntimeError):
    """Mensaje fijo que no incorpora errores remotos o credenciales."""


async def discover_targets(admin):
    request = getattr(admin, '_api_request', None)
    if not callable(request):
        raise AutoAccessError('Se requiere Guacamole real para consultar los escritorios.')
    collection = await request('GET', '/connections')
    if not isinstance(collection, dict):
        raise AutoAccessError('No se pudieron consultar las conexiones RDP.')
    targets = {}
    for identifier, summary in collection.items():
        if not isinstance(summary, dict):
            continue
        protocol = str(summary.get('protocol') or '').lower()
        if protocol and protocol != 'rdp':
            continue
        path = '/connections/' + quote(str(identifier), safe='')
        detail = await request('GET', path)
        if not isinstance(detail, dict):
            raise AutoAccessError('No se pudo consultar el detalle RDP.')
        current = dict(summary)
        current.update(detail)
        if str(current.get('protocol') or '').lower() != 'rdp':
            continue
        official = await request('GET', path + '/parameters')
        if not isinstance(official, dict):
            raise AutoAccessError('No se pudieron conservar las credenciales RDP del laboratorio.')
        parameters = dict(current.get('parameters') or {})
        parameters.update(official)
        host = parameters.get('hostname')
        if host not in LAB_HOSTS:
            continue
        username = parameters.get('username')
        password = parameters.get('password')
        if not isinstance(username, str) or not username or not isinstance(password, str) or not password:
            raise AutoAccessError('Faltan credenciales RDP en un host del laboratorio.')
        identity = (host, username)
        if identity in targets and targets[identity]['password'] != password:
            raise AutoAccessError('Hay credenciales RDP contradictorias para un host del laboratorio.')
        targets[identity] = {'host': host, 'username': username, 'password': password}
    return list(targets.values())


@contextmanager
def connection(target):
    settings = get_settings()
    client = paramiko.SSHClient()
    try:
        if settings.flag_injector_known_hosts:
            client.load_host_keys(settings.flag_injector_known_hosts)
        else:
            client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy() if settings.flag_injector_strict_host_key
                                           else paramiko.AutoAddPolicy())
        client.connect(hostname=target['host'], port=settings.flag_injector_ssh_port,
                       username=target['username'], password=target['password'],
                       timeout=8, banner_timeout=8, auth_timeout=8,
                       allow_agent=False, look_for_keys=False)
        yield client
    finally:
        client.close()


def configure_target(target, *, apply=False):
    command = 'python3 -c ' + shlex.quote(REMOTE_SCRIPT) + (' --apply' if apply else ' --check')
    with connection(target) as client:
        _, stdout, stderr = client.exec_command(command, timeout=120)
        raw = stdout.read(262145)
        # No mostrar stderr: podría contener información de sesión o del servidor.
        stderr.read(16384)
        exit_status = stdout.channel.recv_exit_status()
    try:
        payload = json.loads(raw.decode('utf-8')) if len(raw) <= 262144 else None
    except (ValueError, UnicodeError):
        payload = None
    if exit_status != 0 or not isinstance(payload, dict) or 'error' in payload:
        error = payload.get('error') if isinstance(payload, dict) else None
        if error == 'no-session':
            raise AutoAccessError('No hay una sesión XFCE del usuario RDP con DISPLAY y bus DBus; abre el escritorio antes de aplicar.')
        raise AutoAccessError('No se pudieron consultar, aplicar o verificar las cuatro preferencias XFCE.')
    reports = payload.get('sessions')
    if not isinstance(reports, list) or not reports:
        raise AutoAccessError('La VM no devolvió sesiones XFCE verificables.')
    # Copiar únicamente las cuatro claves y valores booleanos permitidos.
    allowed = ('xfce4-screensaver:/lock/enabled', 'xfce4-screensaver:/lock/sleep-activation',
               'xfce4-screensaver:/saver/idle-activation/enabled',
               'xfce4-power-manager:/xfce4-power-manager/lock-screen-suspend-hibernate')
    safe_reports = []
    for report in reports:
        safe = {}
        for stage in ('before', 'after'):
            values = report.get(stage) if isinstance(report, dict) else None
            if not isinstance(values, dict) or set(values) != set(allowed):
                raise AutoAccessError('La VM no devolvió las cuatro preferencias esperadas.')
            if any(value is not None and type(value) is not bool for value in values.values()):
                raise AutoAccessError('La VM devolvió preferencias XFCE no booleanas.')
            safe[stage] = {key: values[key] for key in allowed}
        safe_reports.append(safe)
    return {'host': target['host'], 'sessions': safe_reports}


async def configure(admin, *, apply=False):
    targets = await discover_targets(admin)
    reports = []
    for target in targets:
        reports.append(await asyncio.to_thread(configure_target, target, apply=apply))
    return reports


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Consultar sin modificar preferencias (predeterminado)')
    mode.add_argument('--apply', action='store_true', help='Desactivar solo los cuatro booleanos en sesiones XFCE existentes')
    args = parser.parse_args()
    try:
        result = await configure(make_guacamole_admin(), apply=args.apply)
    except AutoAccessError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print('No se pudo configurar el acceso automático: ' + type(exc).__name__, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
