"""Servicio SSH deliberadamente débil, limitado al laboratorio CoCiber."""
from __future__ import annotations

import hmac
import os
import socket
import threading
from pathlib import Path

import paramiko

HOST = os.environ.get("DEMO_SSH_HOST", "10.10.30.12")
PORT = int(os.environ.get("DEMO_SSH_PORT", "22222"))
ALLOWED_SOURCE = os.environ.get("DEMO_SSH_ALLOWED_SOURCE", "10.10.20.12")
USERNAME = os.environ["DEMO_SSH_USERNAME"]
PASSWORD = os.environ["DEMO_SSH_PASSWORD"]
FLAG = os.environ["DEMO_SSH_FLAG"]
STATE = Path("/state")


class DemoServer(paramiko.ServerInterface):
    def __init__(self) -> None:
        self.authenticated = False
        self.command = ""
        self.event = threading.Event()

    def check_auth_password(self, username: str, password: str) -> int:
        self.authenticated = hmac.compare_digest(username, USERNAME) and hmac.compare_digest(password, PASSWORD)
        return paramiko.AUTH_SUCCESSFUL if self.authenticated else paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "password"

    def check_channel_request(self, kind: str, chanid: int) -> int:
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *args) -> bool:
        return True

    def check_channel_shell_request(self, channel) -> bool:
        self.command = "shell"
        self.event.set()
        return True

    def check_channel_exec_request(self, channel, command: bytes) -> bool:
        self.command = command.decode("utf-8", "replace").strip()
        self.event.set()
        return True


def answer(command: str) -> str:
    commands = {
        "help": "Comandos permitidos: help, whoami, cat flag.txt, exit\n",
        "whoami": f"{USERNAME}\n",
        "cat flag.txt": f"{FLAG}\n",
        "exit": "Sesión cerrada.\n",
    }
    return commands.get(command, "Shell restringida. Escribe help.\n")


def host_key() -> paramiko.RSAKey:
    STATE.mkdir(parents=True, exist_ok=True)
    path = STATE / "host-rsa.key"
    if not path.exists():
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(str(path))
        path.chmod(0o600)
    return paramiko.RSAKey.from_private_key_file(str(path))


def handle(client: socket.socket, key: paramiko.RSAKey) -> None:
    transport = paramiko.Transport(client)
    transport.get_security_options().kex = ("ecdh-sha2-nistp256",)
    transport.add_server_key(key)
    server = DemoServer()
    try:
        transport.start_server(server=server)
        channel = transport.accept(15)
        if channel is None or not server.event.wait(15):
            return
        if server.command == "shell":
            channel.send("CoCiber SSH demo. Escribe help.\r\n$ ")
            buffer = bytearray()
            while transport.is_active():
                data = channel.recv(1)
                if not data:
                    break
                if data in (b"\r", b"\n"):
                    command = buffer.decode("utf-8", "replace").strip()
                    channel.send("\r\n" + answer(command))
                    if command == "exit":
                        break
                    buffer.clear()
                    channel.send("$ ")
                elif data == b"\x7f":
                    if buffer:
                        buffer.pop()
                elif len(buffer) < 160 and data >= b" ":
                    buffer.extend(data)
                    channel.send(data)
        else:
            channel.send(answer(server.command))
    except (EOFError, OSError, paramiko.SSHException):
        pass
    finally:
        transport.close()
        client.close()


def main() -> None:
    key = host_key()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST, PORT))
        listener.listen(12)
        print(f"CoCiber SSH demo listo en {HOST}:{PORT}; origen permitido: {ALLOWED_SOURCE}", flush=True)
        while True:
            client, address = listener.accept()
            if address[0] != ALLOWED_SOURCE:
                client.close()
                continue
            threading.Thread(target=handle, args=(client, key), daemon=True).start()


if __name__ == "__main__":
    main()
