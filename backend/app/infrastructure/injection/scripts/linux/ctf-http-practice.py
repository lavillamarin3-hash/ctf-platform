"""Dos servicios HTTP didácticos; solo exponen registros de práctica por corrida."""
import argparse
import base64
import binascii
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import threading
import time
from urllib.parse import unquote, urlsplit


PASSWORD_STRATEGY = 'http_password_lab'
FILES_STRATEGY = 'http_files_lab'
VM_LOGIC_STRATEGY = 'vm_logic_lab'
BACKUP_FILE = 'audit-backup.txt'
SERVER_VERSION = '3'


class PracticeHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, address, directory, allowed=('192.168.146.134',)):
        self.directory = Path(directory)
        self.allowed = frozenset(allowed)
        self.gate = threading.BoundedSemaphore(8)
        self.last_activity = time.monotonic()
        super().__init__(address, PracticeHandler)

    def verify_request(self, request, client_address):
        # El puerto del laboratorio admite únicamente la VM atacante indicada.
        request.settimeout(10)
        # La propia víctima puede comprobar solo /__ctf-health/ID; las fuentes
        # del ejercicio continúan limitadas a Kali en el handler.
        return client_address[0] in self.allowed or client_address[0] == '192.168.146.137'

    def process_request(self, request, client_address):
        if not self.gate.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.gate.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.gate.release()

    def record(self, run_id, strategy=None):
        if not re.fullmatch(r'[1-9][0-9]{0,11}', run_id):
            return None
        try:
            # Un nombre construido desde un entero nunca permite rutas del host.
            with (self.directory / ('ctf' + run_id + '.json')).open('rb') as file:
                raw = file.read(262145)
            if len(raw) > 262144:
                return None
            data = json.loads(raw)
            expires = data['expires_at']
            flag = data['flag']
            if (data['strategy'] not in (PASSWORD_STRATEGY, FILES_STRATEGY, VM_LOGIC_STRATEGY)
                    or (strategy is not None and data['strategy'] != strategy) or isinstance(expires, bool)
                    or not isinstance(expires, (int, float)) or not math.isfinite(expires)
                    or expires <= time.time() or not isinstance(flag, str)
                    or not flag.startswith('FLAG{') or not flag.endswith('}')
                    or len(flag) > 2048 or '\r' in flag or '\n' in flag):
                return None
            if data['strategy'] == PASSWORD_STRATEGY:
                digest = data['password_sha256']
                if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
                    return None
            else:
                case = data['case']
                if (not isinstance(case, dict) or not isinstance(case.get('files'), dict)
                        or not isinstance(case.get('web_data'), dict) or len(case['files']) > 128):
                    return None
            return data
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None


class PracticeHandler(BaseHTTPRequestHandler):
    server_version = 'CTFPractice/1'
    sys_version = ''

    def log_message(self, *args):
        # No registrar Authorization, contraseñas, flags ni las cabeceras HTTP.
        pass

    def reply(self, status, body, content_type='text/plain; charset=utf-8', headers=None):
        payload = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-CTF-Practice-Version', SERVER_VERSION)
        self.send_header('Connection', 'close')
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True

    def route(self):
        try:
            parsed = urlsplit(self.path)
            path = unquote(parsed.path, errors='strict')
        except (ValueError, UnicodeError):
            return None
        # Sin alias de rutas, separadores codificados, queries ni segmentos '..'.
        if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
                or path != parsed.path or '\\' in path or '\x00' in path):
            return None
        match = re.fullmatch(r'/practice/([1-9][0-9]{0,11})/([A-Za-z0-9_./-]*)', path)
        if match and (any(part in ('.', '..') for part in match.group(2).split('/')) or '//' in match.group(2)):
            return None
        return match.groups() if match else None

    def json_reply(self, status, data):
        self.reply(status, json.dumps(data, ensure_ascii=False), 'application/json; charset=utf-8')

    def public_file(self, case, resource):
        name = resource + 'index.html' if not resource or resource.endswith('/') else resource
        entry = case['files'].get(name)
        if not isinstance(entry, dict):
            return False
        try:
            body = entry['body']
            content_type = entry['content_type']
            if (not isinstance(body, str) or len(body) > 131072 or content_type not in (
                    'text/plain; charset=utf-8', 'application/json; charset=utf-8',
                    'application/javascript; charset=utf-8', 'text/html; charset=utf-8')):
                return False
            payload = base64.b64decode(body, validate=True)
        except (KeyError, TypeError, ValueError, binascii.Error):
            return False
        self.reply(200, payload, content_type)
        return True

    def authorized(self, run_id, record):
        value = self.headers.get('Authorization', '')
        if not value.startswith('Basic ') or len(value) > 2048:
            return False
        try:
            raw = base64.b64decode(value[6:], validate=True).decode('utf-8')
            username, password = raw.split(':', 1)
        except (ValueError, UnicodeError, binascii.Error):
            return False
        digest = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return (hmac.compare_digest(username.encode('utf-8'), ('ctf' + run_id).encode('utf-8'))
                and hmac.compare_digest(digest, record['password_sha256']))

    def do_GET(self):
        self.server.last_activity = time.monotonic()
        if self.client_address[0] not in self.server.allowed:
            health = re.fullmatch(r'/__ctf-health/([1-9][0-9]{0,11})', self.path)
            if self.client_address[0] == '192.168.146.137' and health and self.server.record(health.group(1)):
                self.reply(200, 'Ready\n')
            else:
                self.reply(403, 'Acceso restringido al laboratorio.\n')
            return
        route = self.route()
        if not route:
            self.reply(404, 'Ruta de práctica inexistente.\n')
            return
        run_id, resource = route
        record = self.server.record(run_id)
        if not record:
            self.reply(404, 'La corrida no existe, ha caducado o está cerrada.\n')
            return
        if record['strategy'] == PASSWORD_STRATEGY:
            if resource != 'private/flag.txt':
                self.reply(404, 'Ruta de práctica inexistente.\n')
                return
            time.sleep(0.15)
            if not self.authorized(run_id, record):
                self.reply(401, 'Credenciales de práctica requeridas.\n', headers={
                    'WWW-Authenticate': 'Basic realm="CTF practice", charset="UTF-8"'})
                return
            # Revalidar después del intento: el cierre/caducidad invalida el acceso.
            record = self.server.record(run_id, PASSWORD_STRATEGY)
            if not record:
                self.reply(404, 'La corrida ha caducado o está cerrada.\n')
                return
            self.reply(200, record['flag'] + '\n')
            return
        case = record['case']
        web = case['web_data']
        if web.get('kind') == 'idor':
            if resource == 'api/profile':
                self.json_reply(200, {'user': web['user'], 'document_ids': [web['own_id']]})
                return
            if resource == 'api/documents':
                self.json_reply(200, {'user': web['user'], 'documents': [web['objects'][str(web['own_id'])]]})
                return
            match = re.fullmatch(r'api/documents/([1-9][0-9]{0,8})', resource)
            if match:
                document = web['objects'].get(match.group(1))
                if document:
                    # Fallo de autorización deliberado, limitado a estos datos
                    # didácticos: comprueba existencia pero omite propietario.
                    self.json_reply(200, document)
                else:
                    self.json_reply(404, {'error': 'Documento inexistente'})
                return
        if not self.public_file(case, resource):
            self.reply(404, 'Ruta de práctica inexistente.\n')

    def do_POST(self):
        self.server.last_activity = time.monotonic()
        if self.client_address[0] not in self.server.allowed:
            self.reply(403, 'Acceso restringido al laboratorio.\n')
            return
        route = self.route()
        if route and route[1] == 'login':
            run_id, _ = route
            record = self.server.record(run_id, VM_LOGIC_STRATEGY)
            if not record:
                self.reply(404, 'La corrida no existe, ha caducado o está cerrada.\n')
                return
            web = record['case']['web_data']
            if web.get('kind') != 'auth':
                self.reply(404, 'Ruta de práctica inexistente.\n')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if (not 0 < length <= 4096 or self.headers.get('Transfer-Encoding')
                        or not self.headers.get('Content-Type', '').startswith('application/json')):
                    raise ValueError('Petición inválida')
                payload = json.loads(self.rfile.read(length))
                if (not isinstance(payload, dict) or set(payload) != {'user', 'password', 'role'}
                        or any(not isinstance(value, str) or len(value) > 256 for value in payload.values())):
                    raise ValueError('Petición inválida')
            except (ValueError, UnicodeError):
                self.json_reply(400, {'error': 'Se requiere JSON con user, password y role de texto'})
                return
            password_ok = hmac.compare_digest(hashlib.sha256(payload['password'].encode()).hexdigest(), web['password_sha256'])
            allowed = payload['user'] == web['user'] and (password_ok or payload['role'] == web['role'])
            if not allowed:
                self.json_reply(401, {'error': 'Acceso denegado'})
                return
            if not self.server.record(run_id, VM_LOGIC_STRATEGY):
                self.reply(404, 'La corrida ha caducado o está cerrada.\n')
                return
            self.json_reply(200, {'session': web['session'], 'user': web['user'], 'role': payload['role'],
                                  'password_verified': password_ok, 'authenticated': True})
            return
        self.reply(405, 'La práctica admite únicamente GET.\n', headers={'Allow': 'GET'})

    def unsupported(self):
        self.reply(405, 'Método no admitido.\n', headers={'Allow': 'GET, POST'})

    do_PUT = unsupported
    do_DELETE = unsupported
    do_PATCH = unsupported
    do_HEAD = unsupported
    do_OPTIONS = unsupported


def has_active_records(directory, *, at=None):
    """La inactividad no acorta una corrida configurada por más de una hora."""
    at = time.time() if at is None else at
    for path in Path(directory).glob('ctf*.json'):
        if not re.fullmatch(r'ctf[1-9][0-9]{0,11}\.json', path.name):
            continue
        try:
            expires = json.loads(path.read_text())['expires_at']
            if (isinstance(expires, (int, float)) and not isinstance(expires, bool)
                    and math.isfinite(expires) and expires > at):
                return True
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return False


def serve(directory, bind='192.168.146.137', port=18082, allowed=('192.168.146.134',)):
    with PracticeHTTPServer((bind, port), directory, allowed) as server:
        server.timeout = 30
        while time.monotonic() - server.last_activity < 3600 or has_active_records(directory):
            server.handle_request()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    serve(args.directory)
