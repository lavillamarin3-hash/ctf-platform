"""SSH didáctico sin shell del sistema. Cuenta y evidencia independientes por corrida."""
import argparse
import hashlib
import hmac
import json
import logging
import math
from pathlib import Path
import re
import socket
import threading
import time
import paramiko

logging.getLogger('paramiko').setLevel(logging.CRITICAL)


class PracticeServer(paramiko.ServerInterface):
    def __init__(self, directory):
        self.directory = Path(directory)
        self.username = None
        self.event = threading.Event()
        self.command = None

    def record(self, username=None):
        name = username or self.username or ''
        if not re.fullmatch(r'ctf[1-9][0-9]{0,11}', name):
            return None
        try:
            data = json.loads((self.directory / (name + '.json')).read_text())
            return data if data['expires_at'] > time.time() else None
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def get_allowed_auths(self, username):
        return 'password'

    def check_auth_password(self, username, password):
        time.sleep(0.15)
        record = self.record(username)
        digest = hashlib.sha256(password.encode()).hexdigest()
        if record and hmac.compare_digest(record['password_sha256'], digest):
            self.username = username
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == 'session' and chanid == 0 else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *args):
        return True

    def check_channel_subsystem_request(self, channel, name):
        return False

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_exec_request(self, channel, command):
        self.command = command.decode('utf-8', errors='replace')[:200]
        self.event.set()
        return True

    def execute(self, command):
        record = self.record()
        if not record:
            return 'La corrida esta cerrada o ha caducado.\n'
        commands = {
            'help': 'Comandos: help, whoami, pwd, ls, cat flag.txt, exit\n',
            'whoami': self.username + '\n', 'pwd': '/practice\n', 'ls': 'flag.txt\n',
            'cat flag.txt': record['flag'] + '\n', 'cat /practice/flag.txt': record['flag'] + '\n',
        }
        return commands.get(command.strip(), 'Shell didactica restringida. Escribe help.\n')


def handle(client, key, directory):
    transport = paramiko.Transport(client)
    # ECDH compatible con libssh/Hydra de la Kali del laboratorio.
    transport.get_security_options().kex = ('ecdh-sha2-nistp256',)
    try:
        transport.add_server_key(key)
        server = PracticeServer(directory)
        transport.start_server(server=server)
        channel = transport.accept(60)
        if channel is None or not server.event.wait(10):
            return
        channel.settimeout(120)
        if server.command is not None:
            channel.sendall(server.execute(server.command).encode())
            channel.send_exit_status(0)
            channel.shutdown_write()
            return
        channel.sendall(b'CTF SSH de practica. Shell restringida; help muestra comandos.\r\n$ ')
        line = bytearray()
        while transport.is_active():
            data = channel.recv(1)
            if not data:
                break
            if data in (b'\r', b'\n'):
                command = line.decode(errors='replace').strip(); line.clear()
                channel.sendall(b'\r\n')
                if command == 'exit': break
                channel.sendall(server.execute(command).replace('\n','\r\n').encode() + b'$ ')
            elif data in (b'\x7f', b'\x08'):
                if line: line.pop(); channel.sendall(b'\b \b')
            elif data == b'\x03':
                line.clear(); channel.sendall(b'^C\r\n$ ')
            elif len(line) < 200 and data >= b' ':
                line.extend(data); channel.sendall(data)
    except (EOFError, OSError, paramiko.SSHException) as exc:
        print('SSH practice transport:',type(exc).__name__,str(exc)[:160],flush=True)
    finally:
        transport.close(); client.close()


def has_active_records(directory, *, at=None):
    """No apagar por inactividad mientras una práctica conserve su plazo real."""
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


def serve(directory, bind='10.10.30.12', port=2222, allowed=('10.10.20.10', '10.10.20.11', '10.10.20.12')):
    directory = Path(directory)
    key_path = directory / 'host-key'
    if not key_path.exists():
        paramiko.RSAKey.generate(2048).write_private_key_file(str(key_path))
        key_path.chmod(0o600)
    key = paramiko.RSAKey.from_private_key_file(str(key_path))
    gate = threading.BoundedSemaphore(8)
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((bind,port)); listener.listen(8); listener.settimeout(30)
        last = time.time()
        while time.time()-last < 3600 or has_active_records(directory):
            try: client, address = listener.accept()
            except socket.timeout: continue
            if address[0] not in allowed or not gate.acquire(blocking=False):
                client.close(); continue
            last = time.time()
            def worker(client=client):
                try: handle(client,key,directory)
                finally: gate.release()
            threading.Thread(target=worker,daemon=True).start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory',required=True)
    args = parser.parse_args()
    serve(args.directory)
