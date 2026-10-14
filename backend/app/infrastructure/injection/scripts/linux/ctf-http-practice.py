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
BACKUP_FILE = 'audit-backup.txt'


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
        return client_address[0] in self.allowed

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

    def record(self, run_id, strategy):
        if not re.fullmatch(r'[1-9][0-9]{0,11}', run_id):
            return None
        try:
            # Un nombre construido desde un entero nunca permite rutas del host.
            with (self.directory / ('ctf' + run_id + '.json')).open('rb') as file:
                raw = file.read(16385)
            if len(raw) > 16384:
                return None
            data = json.loads(raw)
            expires = data['expires_at']
            flag = data['flag']
            if (data['strategy'] != strategy or isinstance(expires, bool)
                    or not isinstance(expires, (int, float)) or not math.isfinite(expires)
                    or expires <= time.time() or not isinstance(flag, str)
                    or not flag.startswith('FLAG{') or not flag.endswith('}')
                    or len(flag) > 2048 or '\r' in flag or '\n' in flag):
                return None
            if strategy == PASSWORD_STRATEGY:
                digest = data['password_sha256']
                if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
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
        payload = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
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
        match = re.fullmatch(r'/practice/([1-9][0-9]{0,11})/(robots\.txt|backup/|backup/audit-backup\.txt|private/flag\.txt)', path)
        return match.groups() if match else None

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
        route = self.route()
        if not route:
            self.reply(404, 'Ruta de práctica inexistente.\n')
            return
        run_id, resource = route
        strategy = PASSWORD_STRATEGY if resource == 'private/flag.txt' else FILES_STRATEGY
        record = self.server.record(run_id, strategy)
        if not record:
            self.reply(404, 'La corrida no existe, ha caducado o está cerrada.\n')
            return
        if strategy == PASSWORD_STRATEGY:
            time.sleep(0.15)
            if not self.authorized(run_id, record):
                self.reply(401, 'Credenciales de práctica requeridas.\n', headers={
                    'WWW-Authenticate': 'Basic realm="CTF practice", charset="UTF-8"'})
                return
            # Revalidar después del intento: el cierre/caducidad invalida el acceso.
            record = self.server.record(run_id, strategy)
            if not record:
                self.reply(404, 'La corrida ha caducado o está cerrada.\n')
                return
            self.reply(200, record['flag'] + '\n')
            return
        if resource == 'robots.txt':
            self.reply(200, 'User-agent: *\nDisallow: /practice/' + run_id + '/backup/\n')
        elif resource == 'backup/':
            self.reply(200, '<!doctype html><html lang="es"><meta charset="utf-8">'
                       '<title>Backup de práctica</title><h1>Archivos de respaldo</h1>'
                       '<a href="' + BACKUP_FILE + '">' + BACKUP_FILE + '</a></html>\n',
                       'text/html; charset=utf-8')
        else:
            self.reply(200, 'Respaldo didáctico generado para esta corrida.\n' + record['flag'] + '\n')

    def do_POST(self):
        self.reply(405, 'La práctica admite únicamente GET.\n', headers={'Allow': 'GET'})

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST
    do_HEAD = do_POST
    do_OPTIONS = do_POST


def serve(directory, bind='192.168.146.137', port=18082, allowed=('192.168.146.134',)):
    with PracticeHTTPServer((bind, port), directory, allowed) as server:
        server.timeout = 30
        while time.monotonic() - server.last_activity < 3600:
            server.handle_request()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    serve(args.directory)
