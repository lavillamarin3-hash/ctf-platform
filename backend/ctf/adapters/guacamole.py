"""Reutiliza el cliente Guacamole existente; sesiones efímeras por corrida."""
import base64
import hashlib
import json
import secrets
from urllib.parse import quote
from urllib.request import Request
from cryptography.fernet import Fernet
from app.guacamole import ManagedGuacamoleAdapter, GuacamoleApiError


class Guacamole(ManagedGuacamoleAdapter):
    def __init__(self, settings, cache):
        self.base_url = settings.guacamole_api_url.rstrip("/").removesuffix("/api")
        self.service_account = settings.guacamole_admin_user
        self.service_password = settings.guacamole_admin_password.get_secret_value()
        self.datasource = settings.guacamole_datasource
        self.cache = cache.client
        self.cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.get_secret_value().encode()).digest()))

    async def create(self, run_id, host, password):
        username = f"ctf_{run_id}"
        guac_password = secrets.token_urlsafe(32)
        await self.create_user(username, guac_password)
        connection = await self.create_connection(name=username, protocol="ssh", hostname=host, port=22, username=username, password=password)
        await self.patch_user_permissions(username, system_permissions=[], connection_permissions={connection.identifier: ["READ"]})
        delegated = await self.authenticate_player(username, guac_password)
        if delegated["data_source"] != self.datasource: raise RuntimeError("Datasource no corresponde")
        await self.cache.set(f"terminal:session:{run_id}", self.cipher.encrypt(json.dumps(delegated).encode()).decode(), ex=7200)
        return connection.identifier

    async def session(self, run_id):
        value = await self.cache.get(f"terminal:session:{run_id}")
        if not value: raise RuntimeError("Terminal sin sesión")
        return json.loads(self.cipher.decrypt(value.encode()))

    async def destroy(self, run_id):
        username = f"ctf_{run_id}"
        # Recupera IDs por nombre incluso si create perdió su respuesta.
        connections = await self.list_connections()
        for connection in connections:
            if connection.name == username:
                try: await self.delete_connection(connection.identifier)
                except GuacamoleApiError as exc:
                    if exc.status_code != 404: raise
        try: await self.delete_user(username)
        except GuacamoleApiError as exc:
            if exc.status_code != 404: raise
        value = await self.cache.get(f"terminal:session:{run_id}")
        if value:
            delegated = json.loads(self.cipher.decrypt(value.encode()))
            try: await self._blocking_request(Request(f"{self.base_url}/api/tokens/{quote(delegated['token'], safe='')}", method="DELETE"))
            except GuacamoleApiError as exc:
                if exc.status_code not in (401, 404): raise
        await self.cache.delete(f"terminal:session:{run_id}")
