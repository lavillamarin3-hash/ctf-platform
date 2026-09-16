# ============================================================
# ADAPTADORES DE GUACAMOLE
# Responsabilidad: encapsular autenticación HTTP, usuarios,
# conexiones y permisos de Guacamole.
# ============================================================

from __future__ import annotations

import asyncio
import base64
import json

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .core import get_settings


# ============================================================
# MODELOS
# ============================================================

@dataclass(frozen=True)
class RemoteConnection:
    external_reference: str
    launch_url: str


@dataclass(frozen=True)
class GuacamoleUser:
    username: str
    attributes: dict
    last_active: int | None = None


@dataclass(frozen=True)
class GuacamoleConnection:
    identifier: str
    name: str
    protocol: str
    parent_identifier: str = "ROOT"
    hostname: str | None = None
    port: str | None = None
    parameters: dict | None = None
    attributes: dict | None = None
    active_connections: int = 0


# ============================================================
# EXCEPCIONES
# ============================================================

class GuacamoleApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


# ============================================================
# PUERTOS
# ============================================================

class RemoteAccessProvisioningPort:

    async def provision(
        self,
        username: str,
        challenge_code: str,
        run_id: int,
    ) -> RemoteConnection:
        raise NotImplementedError

    async def revoke(self, external_reference: str) -> None:
        raise NotImplementedError


class GuacamoleAdminPort:

    async def list_users(self) -> list[GuacamoleUser]:
        raise NotImplementedError

    async def list_user_groups(self) -> list[dict]:
        raise NotImplementedError

    async def create_user_group(
        self,
        identifier: str,
        *,
        disabled: bool = False,
    ) -> dict:
        raise NotImplementedError

    async def update_user_group(
        self,
        identifier: str,
        *,
        disabled: bool = False,
    ) -> dict:
        raise NotImplementedError

    async def delete_user_group(self, identifier: str) -> None:
        raise NotImplementedError

    async def add_user_group_member(
        self,
        identifier: str,
        username: str,
    ) -> None:
        raise NotImplementedError

    async def remove_user_group_member(
        self,
        identifier: str,
        username: str,
    ) -> None:
        raise NotImplementedError

    async def get_user_group_permissions(
        self,
        identifier: str,
    ) -> dict:
        raise NotImplementedError

    async def patch_user_group_permissions(
        self,
        identifier: str,
        *,
        connection_permissions: dict[str, list[str]],
    ) -> dict:
        raise NotImplementedError

    async def create_user(
        self,
        username: str,
        password: str,
        *,
        email: str | None = None,
        full_name: str | None = None,
    ) -> GuacamoleUser:
        raise NotImplementedError

    async def update_user(
        self,
        username: str,
        *,
        password: str | None = None,
        email: str | None = None,
        full_name: str | None = None,
        disabled: bool | None = None,
    ) -> GuacamoleUser:
        raise NotImplementedError

    async def delete_user(self, username: str) -> None:
        raise NotImplementedError

    async def list_connections(self) -> list[GuacamoleConnection]:
        raise NotImplementedError

    async def create_connection(
        self,
        *,
        name: str,
        protocol: str,
        hostname: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        domain: str | None = None,
        parent_identifier: str = "ROOT",
    ) -> GuacamoleConnection:
        raise NotImplementedError

    async def clone_connection(
        self,
        source_identifier: str,
        *,
        name: str,
        parent_identifier: str = "ROOT",
    ) -> GuacamoleConnection:
        raise NotImplementedError

    async def update_connection(
        self,
        identifier: str,
        *,
        name: str,
        protocol: str,
        hostname: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        domain: str | None = None,
        parent_identifier: str = "ROOT",
    ) -> GuacamoleConnection:
        raise NotImplementedError

    async def delete_connection(self, identifier: str) -> None:
        raise NotImplementedError

    async def get_user_permissions(self, username: str) -> dict:
        raise NotImplementedError

    async def patch_user_permissions(
        self,
        username: str,
        *,
        system_permissions: list[str],
        connection_permissions: dict[str, list[str]],
    ) -> dict:
        raise NotImplementedError

    async def status(self) -> dict:
        raise NotImplementedError


# ============================================================
# ADAPTADOR STUB
# ============================================================

class StubGuacamoleAdapter(
    RemoteAccessProvisioningPort,
    GuacamoleAdminPort,
):

    def __init__(self) -> None:
        self.users: dict[str, GuacamoleUser] = {
            "guacadmin": GuacamoleUser("guacadmin", {})
        }

        self.connections: dict[str, GuacamoleConnection] = {}

        self.permissions: dict[str, dict] = {
            "guacadmin": {
                "systemPermissions": ["ADMINISTER"],
                "connectionPermissions": {},
            }
        }

        self._next_connection = 1

    async def provision(
        self,
        username: str,
        challenge_code: str,
        run_id: int,
    ) -> RemoteConnection:

        settings = get_settings()

        ref = (
            f"ctf-{username}-"
            f"{challenge_code.lower()}-"
            f"{run_id}"
        )

        return RemoteConnection(
            ref,
            f"{settings.guacamole_base_url.rstrip('/')}/#/home",
        )

    async def revoke(self, external_reference: str) -> None:
        return None

    async def direct_connection_url(
        self,
        identifier: str,
    ) -> str:

        settings = get_settings()

        return (
            f"{settings.guacamole_base_url.rstrip('/')}"
            f"/#/client/{identifier}"
        )

    async def list_users(self) -> list[GuacamoleUser]:
        return list(self.users.values())

    async def list_user_groups(self) -> list[dict]:

        return [
            {
                "identifier": key,
                "attributes": {},
                "disabled": False,
                "memberUsers": [],
            }
            for key in self.permissions.get("__groups__", {}).keys()
        ]

    async def create_user_group(
        self,
        identifier: str,
        *,
        disabled: bool = False,
    ) -> dict:

        groups = self.permissions.setdefault("__groups__", {})

        if identifier in groups:
            raise GuacamoleApiError(
                "El grupo ya existe en Guacamole",
                409,
            )

        groups[identifier] = {
            "disabled": disabled,
            "members": set(),
            "connectionPermissions": {},
        }

        return {
            "identifier": identifier,
            "attributes": {},
            "disabled": disabled,
        }

    async def update_user_group(
        self,
        identifier: str,
        *,
        disabled: bool = False,
    ) -> dict:

        groups = self.permissions.setdefault("__groups__", {})

        if identifier not in groups:
            raise GuacamoleApiError(
                "Grupo no encontrado",
                404,
            )

        groups[identifier]["disabled"] = disabled

        return {
            "identifier": identifier,
            "attributes": {},
            "disabled": disabled,
        }

    async def delete_user_group(
        self,
        identifier: str,
    ) -> None:

        groups = self.permissions.setdefault("__groups__", {})

        groups.pop(identifier, None)

    async def add_user_group_member(
        self,
        identifier: str,
        username: str,
    ) -> None:

        groups = self.permissions.setdefault("__groups__", {})

        if identifier not in groups:
            raise GuacamoleApiError(
                "Grupo no encontrado",
                404,
            )

        groups[identifier]["members"].add(username)

    async def remove_user_group_member(
        self,
        identifier: str,
        username: str,
    ) -> None:

        groups = self.permissions.setdefault("__groups__", {})

        if identifier in groups:
            groups[identifier]["members"].discard(username)

    async def get_user_group_permissions(
        self,
        identifier: str,
    ) -> dict:

        groups = self.permissions.setdefault("__groups__", {})

        if identifier not in groups:
            raise GuacamoleApiError(
                "Grupo no encontrado",
                404,
            )

        return {
            "connectionPermissions": groups[identifier].get(
                "connectionPermissions",
                {},
            )
        }

    async def patch_user_group_permissions(
        self,
        identifier: str,
        *,
        connection_permissions: dict[str, list[str]],
    ) -> dict:

        groups = self.permissions.setdefault("__groups__", {})

        if identifier not in groups:
            raise GuacamoleApiError(
                "Grupo no encontrado",
                404,
            )

        groups[identifier]["connectionPermissions"] = (
            connection_permissions
        )

        return {
            "connectionPermissions": connection_permissions
        }

    async def create_user(
        self,
        username: str,
        password: str,
        *,
        email=None,
        full_name=None,
    ) -> GuacamoleUser:

        if username in self.users:
            raise GuacamoleApiError(
                "El usuario ya existe",
                409,
            )

        user = GuacamoleUser(
            username,
            {
                "guac-email-address": email,
                "guac-full-name": full_name,
                "disabled": None,
            },
        )

        self.users[username] = user

        self.permissions[username] = {
            "systemPermissions": [],
            "connectionPermissions": {},
        }

        return user

    async def update_user(
        self,
        username: str,
        *,
        password=None,
        email=None,
        full_name=None,
        disabled=None,
    ) -> GuacamoleUser:

        if username not in self.users:
            raise GuacamoleApiError(
                "Usuario no encontrado",
                404,
            )

        attributes = dict(
            self.users[username].attributes
        )

        if email is not None:
            attributes["guac-email-address"] = email

        if full_name is not None:
            attributes["guac-full-name"] = full_name

        if disabled is not None:
            attributes["disabled"] = (
                "true" if disabled else None
            )

        user = GuacamoleUser(
            username,
            attributes,
        )

        self.users[username] = user

        return user

    async def delete_user(self, username: str) -> None:

        if username == "guacadmin":
            raise GuacamoleApiError(
                "No puedes eliminar guacadmin",
                409,
            )

        self.users.pop(username, None)
        self.permissions.pop(username, None)

    async def list_connections(
        self,
    ) -> list[GuacamoleConnection]:

        return list(self.connections.values())

    async def clone_connection(
        self,
        source_identifier: str,
        *,
        name: str,
        parent_identifier: str = "ROOT",
    ) -> GuacamoleConnection:

        source = self.connections.get(source_identifier)

        if source is None:
            raise GuacamoleApiError(
                "Conexión origen no encontrada",
                404,
            )

        params = dict(source.parameters or {})

        return await self.create_connection(
            name=name,
            protocol=source.protocol,
            hostname=(
                source.hostname
                or params.get("hostname")
                or ""
            ),
            port=int(
                source.port
                or params.get("port")
                or 22
            ),
            username=params.get("username"),
            password=params.get("password"),
            domain=params.get("domain"),
            parent_identifier=parent_identifier,
        )

    async def create_connection(
        self,
        *,
        name,
        protocol,
        hostname,
        port,
        username=None,
        password=None,
        domain=None,
        parent_identifier="ROOT",
    ):

        identifier = str(self._next_connection)

        self._next_connection += 1

        params = {
            "hostname": hostname,
            "port": str(port),
        }

        if username is not None:
            params["username"] = username

        if password is not None:
            params["password"] = password

        if domain is not None:
            params["domain"] = domain

        connection = GuacamoleConnection(
            identifier,
            name,
            protocol,
            parent_identifier,
            str(hostname),
            str(port),
            params,
            {},
            0,
        )

        self.connections[identifier] = connection

        return connection

    async def update_connection(
        self,
        identifier: str,
        *,
        name,
        protocol,
        hostname,
        port,
        username=None,
        password=None,
        domain=None,
        parent_identifier="ROOT",
    ):

        if identifier not in self.connections:
            raise GuacamoleApiError(
                "Conexión no encontrada",
                404,
            )

        old = self.connections[identifier]

        params = dict(old.parameters or {})

        params.update(
            {
                "hostname": hostname,
                "port": str(port),
            }
        )

        if username is not None:
            params["username"] = username

        if password is not None:
            params["password"] = password

        if domain is not None:
            params["domain"] = domain

        connection = GuacamoleConnection(
            identifier,
            name,
            protocol,
            parent_identifier,
            hostname,
            str(port),
            params,
            old.attributes or {},
            old.active_connections,
        )

        self.connections[identifier] = connection

        return connection

    async def delete_connection(
        self,
        identifier: str,
    ) -> None:

        self.connections.pop(identifier, None)

    async def get_user_permissions(
        self,
        username: str,
    ) -> dict:

        return self.permissions.get(
            username,
            {
                "systemPermissions": [],
                "connectionPermissions": {},
            },
        )

    async def patch_user_permissions(
        self,
        username: str,
        *,
        system_permissions,
        connection_permissions,
    ) -> dict:

        if username not in self.users:
            raise GuacamoleApiError(
                "Usuario no encontrado",
                404,
            )

        self.permissions[username] = {
            "systemPermissions": system_permissions,
            "connectionPermissions": connection_permissions,
        }

        return self.permissions[username]

    async def status(self) -> dict:

        settings = get_settings()

        return {
            "mode": "stub",
            "connected": True,
            "base_url": settings.guacamole_base_url,
            "data_source": "stub",
            "username": settings.guacamole_service_account or "stub",
            "user_count": len(self.users),
        }


# ============================================================
# ADAPTADOR REAL
# ============================================================

class ManagedGuacamoleAdapter(
    RemoteAccessProvisioningPort,
    GuacamoleAdminPort,
):

    def __init__(self) -> None:

        settings = get_settings()

        self.base_url = (
            settings.guacamole_api_url
            or settings.guacamole_base_url
        ).rstrip("/")

        self.service_account = (
            settings.guacamole_service_account
        )

        self.service_password = (
            settings.guacamole_service_password
        )

        if (
            not self.service_account
            or not self.service_password
        ):
            raise RuntimeError(
                "GUACAMOLE_SERVICE_ACCOUNT y "
                "GUACAMOLE_SERVICE_PASSWORD son obligatorios "
                "en modo real"
            )

    async def _blocking_request(
        self,
        request: Request,
    ) -> tuple[int, bytes]:

        def do():

            try:
                with urlopen(
                    request,
                    timeout=15,
                ) as response:

                    return (
                        int(response.status),
                        response.read(),
                    )

            except HTTPError as exc:

                body = exc.read().decode(
                    "utf-8",
                    "ignore",
                )

                raise GuacamoleApiError(
                    f"Guacamole respondió HTTP {exc.code}",
                    exc.code,
                    body[:2000],
                ) from exc

            except URLError as exc:

                raise GuacamoleApiError(
                    f"No se pudo contactar con Guacamole: "
                    f"{exc.reason}"
                ) from exc

        return await asyncio.to_thread(do)

    async def _post_token(self):

        body = urlencode(
            {
                "username": self.service_account,
                "password": self.service_password,
            }
        ).encode()

        request = Request(
            f"{self.base_url}/api/tokens",
            data=body,
            method="POST",
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded"
            },
        )

        _, raw = await self._blocking_request(
            request
        )

        payload = json.loads(
            raw.decode()
        )

        token = payload.get("authToken")
        data_source = payload.get("dataSource")

        if not token or not data_source:
            raise GuacamoleApiError(
                "Guacamole no devolvió "
                "authToken/dataSource"
            )

        return token, data_source

    async def _api_request(
        self,
        method: str,
        path: str,
        *,
        data: dict | list | None = None,
    ):

        token, data_source = await self._post_token()

        separator = (
            "&" if "?" in path else "?"
        )

        url = (
            f"{self.base_url}/api/session/data/"
            f"{quote(data_source, safe='')}"
            f"{path}"
            f"{separator}token="
            f"{quote(token, safe='')}"
        )

        body = None

        headers = {
            "Accept": "application/json"
        }

        if data is not None:

            body = json.dumps(
                data
            ).encode()

            headers["Content-Type"] = (
                "application/json"
            )

        request = Request(
            url,
            data=body,
            method=method,
            headers=headers,
        )

        _, raw = await self._blocking_request(
            request
        )

        return (
            json.loads(raw.decode())
            if raw
            else None
        )

    @staticmethod
    def _user(payload):

        return GuacamoleUser(
            str(
                payload.get(
                    "username",
                    "",
                )
            ),
            dict(
                payload.get(
                    "attributes"
                )
                or {}
            ),
            payload.get(
                "lastActive"
            ),
        )

    @staticmethod
    def _conn(
        identifier,
        payload,
    ):

        params = dict(
            payload.get(
                "parameters"
            )
            or {}
        )

        attributes = dict(
            payload.get(
                "attributes"
            )
            or {}
        )

        return GuacamoleConnection(
            str(identifier),
            str(
                payload.get(
                    "name",
                    "",
                )
            ),
            str(
                payload.get(
                    "protocol",
                    "",
                )
            ),
            str(
                payload.get(
                    "parentIdentifier"
                )
                or "ROOT"
            ),
            params.get(
                "hostname"
            ),
            params.get(
                "port"
            ),
            params,
            attributes,
            int(
                payload.get(
                    "activeConnections"
                )
                or 0
            ),
        )

    # ========================================================
    # STATUS
    # ========================================================

    async def status(self):

        users = await self.list_users()

        token, data_source = (
            await self._post_token()
        )

        _ = token

        return {
            "mode": "real",
            "connected": True,
            "base_url": self.base_url,
            "data_source": data_source,
            "username": self.service_account,
            "user_count": len(users),
        }

    # ========================================================
    # USERS
    # ========================================================

    async def list_users(self):

        payload = await self._api_request(
            "GET",
            "/users",
        )

        return [
            self._user(item)
            for item in payload.values()
        ] if isinstance(payload, dict) else []

    async def create_user(
        self,
        username,
        password,
        *,
        email=None,
        full_name=None,
    ):

        attributes = {
            "guac-email-address": email,
            "guac-full-name": full_name,
            "expired": None,
            "disabled": None,
            "timezone": None,
            "valid-from": None,
            "valid-until": None,
            "access-window-start": None,
            "access-window-end": None,
            "guac-organization": None,
            "guac-organizational-role": None,
        }

        payload = await self._api_request(
            "POST",
            "/users",
            data={
                "username": username,
                "password": password,
                "attributes": attributes,
            },
        )

        return self._user(
            payload
            if isinstance(payload, dict)
            else {
                "username": username,
                "attributes": attributes,
            }
        )

    async def update_user(
        self,
        username,
        *,
        password=None,
        email=None,
        full_name=None,
        disabled=None,
    ):

        users = await self._api_request(
            "GET",
            "/users",
        )

        if (
            not isinstance(users, dict)
            or username not in users
        ):
            raise GuacamoleApiError(
                f"El usuario de Guacamole "
                f"'{username}' no existe",
                404,
            )

        current = dict(
            users[username]
        )

        current["username"] = username

        attributes = dict(
            current.get(
                "attributes"
            )
            or {}
        )

        if email is not None:
            attributes["guac-email-address"] = email

        if full_name is not None:
            attributes["guac-full-name"] = full_name

        if disabled is not None:
            attributes["disabled"] = (
                "true" if disabled else None
            )

        current["attributes"] = attributes

        if password is not None:
            current["password"] = password

        payload = await self._api_request(
            "PUT",
            f"/users/{quote(username, safe='')}",
            data=current,
        )

        return self._user(
            payload
            if isinstance(payload, dict)
            else current
        )

    async def delete_user(
        self,
        username,
    ):

        await self._api_request(
            "DELETE",
            f"/users/{quote(username, safe='')}",
        )

    # ========================================================
    # USER GROUPS
    # ========================================================

    async def list_user_groups(self):

        payload = await self._api_request(
            "GET",
            "/userGroups",
        )

        rows = (
            payload.values()
            if isinstance(payload, dict)
            else []
        )

        return [
            dict(item)
            for item in rows
            if isinstance(item, dict)
        ]

    async def create_user_group(
        self,
        identifier: str,
        *,
        disabled: bool = False,
    ):

        payload = {
            "identifier": identifier,
            "attributes": {},
            "disabled": bool(disabled),
        }

        result = await self._api_request(
            "POST",
            "/userGroups",
            data=payload,
        )

        return dict(
            result or payload
        )

    async def update_user_group(
        self,
        identifier: str,
        *,
        disabled: bool = False,
    ):

        payload = {
            "identifier": identifier,
            "attributes": {},
            "disabled": bool(disabled),
        }

        result = await self._api_request(
            "PUT",
            f"/userGroups/{quote(identifier, safe='')}",
            data=payload,
        )

        return dict(
            result or payload
        )

    async def delete_user_group(
        self,
        identifier: str,
    ):

        await self._api_request(
            "DELETE",
            f"/userGroups/{quote(identifier, safe='')}",
        )

    async def add_user_group_member(
        self,
        identifier: str,
        username: str,
    ):

        await self._api_request(
            "PATCH",
            f"/userGroups/{quote(identifier, safe='')}"
            "/memberUsers",
            data=[
                {
                    "op": "add",
                    "path": "/",
                    "value": username,
                }
            ],
        )

    async def remove_user_group_member(
        self,
        identifier: str,
        username: str,
    ):

        await self._api_request(
            "PATCH",
            f"/userGroups/{quote(identifier, safe='')}"
            "/memberUsers",
            data=[
                {
                    "op": "remove",
                    "path": "/",
                    "value": username,
                }
            ],
        )

    async def get_user_group_permissions(
        self,
        identifier: str,
    ):

        payload = await self._api_request(
            "GET",
            f"/userGroups/{quote(identifier, safe='')}"
            "/permissions",
        )

        if not isinstance(payload, dict):
            return {
                "connectionPermissions": {}
            }

        connection_permissions = (
            payload.get(
                "connectionPermissions"
            )
            or {}
        )

        if isinstance(
            connection_permissions,
            list,
        ):
            connection_permissions = {
                str(item): []
                for item
                in connection_permissions
            }

        return {
            "connectionPermissions": {
                str(key): list(value or [])
                for key, value
                in connection_permissions.items()
            }
        }

    async def patch_user_group_permissions(
        self,
        identifier: str,
        *,
        connection_permissions: dict[str, list[str]],
    ):

        current = await self.get_user_group_permissions(
            identifier
        )

        old = current.get(
            "connectionPermissions",
            {},
        )

        operations = []

        for connection_id in (
            set(old)
            | set(connection_permissions)
        ):

            old_permissions = set(
                old.get(
                    connection_id,
                    [],
                )
            )

            new_permissions = set(
                connection_permissions.get(
                    connection_id,
                    [],
                )
            )

            for permission in sorted(
                old_permissions - new_permissions
            ):

                operations.append(
                    {
                        "op": "remove",
                        "path":
                            f"/connectionPermissions/"
                            f"{quote(str(connection_id), safe='')}",
                        "value": permission,
                    }
                )

            for permission in sorted(
                new_permissions - old_permissions
            ):

                operations.append(
                    {
                        "op": "add",
                        "path":
                            f"/connectionPermissions/"
                            f"{quote(str(connection_id), safe='')}",
                        "value": permission,
                    }
                )

        if operations:

            await self._api_request(
                "PATCH",
                f"/userGroups/{quote(identifier, safe='')}"
                "/permissions",
                data=operations,
            )

        return await self.get_user_group_permissions(
            identifier
        )

    # ========================================================
    # CONNECTIONS
    # ========================================================

    async def list_connections(self):

        payload = await self._api_request(
            "GET",
            "/connections",
        )

        return [
            self._conn(
                identifier,
                connection,
            )
            for identifier, connection
            in (
                payload or {}
            ).items()
        ] if isinstance(
            payload,
            dict,
        ) else []

    async def clone_connection(
        self,
        source_identifier: str,
        *,
        name: str,
        parent_identifier: str = "ROOT",
    ):

        payload = await self._api_request(
            "GET",
            f"/connections/"
            f"{quote(source_identifier, safe='')}",
        )

        if not isinstance(payload, dict):
            raise GuacamoleApiError(
                "Conexión origen no encontrada",
                404,
            )

        clone_payload = {
            "parentIdentifier": parent_identifier,
            "name": name,
            "protocol": (
                payload.get("protocol")
                or "ssh"
            ),
            "parameters": dict(
                payload.get(
                    "parameters"
                )
                or {}
            ),
            "attributes": dict(
                payload.get(
                    "attributes"
                )
                or {}
            ),
        }

        created = await self._api_request(
            "POST",
            "/connections",
            data=clone_payload,
        )

        return self._conn(
            (
                created or {}
            ).get(
                "identifier",
                "",
            ),
            created or clone_payload,
        )

    async def create_connection(
        self,
        *,
        name,
        protocol,
        hostname,
        port,
        username=None,
        password=None,
        domain=None,
        parent_identifier="ROOT",
    ):

        parameters = {
            "hostname": hostname,
            "port": str(port),
        }

        if username is not None:
            parameters["username"] = username

        if password is not None:
            parameters["password"] = password

        if domain is not None:
            parameters["domain"] = domain

        payload = await self._api_request(
            "POST",
            "/connections",
            data={
                "parentIdentifier": parent_identifier,
                "name": name,
                "protocol": protocol,
                "parameters": parameters,
                "attributes": {},
            },
        )

        return self._conn(
            (
                payload or {}
            ).get(
                "identifier",
                "",
            ),
            payload or {
                "name": name,
                "protocol": protocol,
                "parameters": parameters,
                "attributes": {},
            },
        )

    async def update_connection(
        self,
        identifier,
        *,
        name,
        protocol,
        hostname,
        port,
        username=None,
        password=None,
        domain=None,
        parent_identifier="ROOT",
    ):

        payload = await self._api_request(
            "GET",
            f"/connections/"
            f"{quote(identifier, safe='')}",
        )

        if not isinstance(payload, dict):
            raise GuacamoleApiError(
                "Conexión no encontrada",
                404,
            )

        parameters = dict(
            payload.get(
                "parameters"
            )
            or {}
        )

        parameters.update(
            {
                "hostname": hostname,
                "port": str(port),
            }
        )

        if username is not None:
            parameters["username"] = username

        if password is not None:
            parameters["password"] = password

        if domain is not None:
            parameters["domain"] = domain

        body = {
            "parentIdentifier":
                parent_identifier,
            "name": name,
            "protocol": protocol,
            "identifier": identifier,
            "activeConnections":
                payload.get(
                    "activeConnections",
                    0,
                ),
            "parameters": parameters,
            "attributes": dict(
                payload.get(
                    "attributes"
                )
                or {}
            ),
        }

        await self._api_request(
            "PUT",
            f"/connections/"
            f"{quote(identifier, safe='')}",
            data=body,
        )

        return self._conn(
            identifier,
            body,
        )

    async def delete_connection(
        self,
        identifier,
    ):

        await self._api_request(
            "DELETE",
            f"/connections/"
            f"{quote(identifier, safe='')}",
        )

    # ========================================================
    # USER PERMISSIONS
    # ========================================================

    async def get_user_permissions(
        self,
        username,
    ):

        payload = await self._api_request(
            "GET",
            f"/users/"
            f"{quote(username, safe='')}"
            "/permissions",
        )

        if not isinstance(payload, dict):
            return {
                "systemPermissions": [],
                "connectionPermissions": {},
            }

        connection_permissions = (
            payload.get(
                "connectionPermissions"
            )
            or {}
        )

        if isinstance(
            connection_permissions,
            list,
        ):
            connection_permissions = {
                str(item): []
                for item
                in connection_permissions
            }

        return {
            "systemPermissions": list(
                payload.get(
                    "systemPermissions"
                )
                or []
            ),
            "connectionPermissions": {
                str(key): list(value or [])
                for key, value
                in connection_permissions.items()
            },
        }

    async def patch_user_permissions(
        self,
        username,
        *,
        system_permissions,
        connection_permissions,
    ):

        current = await self.get_user_permissions(
            username
        )

        operations = []

        old_system = set(
            current["systemPermissions"]
        )

        new_system = set(
            system_permissions
        )

        for permission in sorted(
            old_system - new_system
        ):

            operations.append(
                {
                    "op": "remove",
                    "path": "/systemPermissions",
                    "value": permission,
                }
            )

        for permission in sorted(
            new_system - old_system
        ):

            operations.append(
                {
                    "op": "add",
                    "path": "/systemPermissions",
                    "value": permission,
                }
            )

        old_connections = (
            current[
                "connectionPermissions"
            ]
        )

        connection_ids = (
            set(old_connections)
            | set(connection_permissions)
        )

        for connection_id in connection_ids:

            old_permissions = set(
                old_connections.get(
                    connection_id,
                    [],
                )
            )

            new_permissions = set(
                connection_permissions.get(
                    connection_id,
                    [],
                )
            )

            for permission in sorted(
                old_permissions - new_permissions
            ):

                operations.append(
                    {
                        "op": "remove",
                        "path":
                            f"/connectionPermissions/"
                            f"{quote(str(connection_id), safe='')}",
                        "value": permission,
                    }
                )

            for permission in sorted(
                new_permissions - old_permissions
            ):

                operations.append(
                    {
                        "op": "add",
                        "path":
                            f"/connectionPermissions/"
                            f"{quote(str(connection_id), safe='')}",
                        "value": permission,
                    }
                )

        if operations:

            await self._api_request(
                "PATCH",
                f"/users/"
                f"{quote(username, safe='')}"
                "/permissions",
                data=operations,
            )

        return await self.get_user_permissions(
            username
        )

    # ========================================================
    # PROVISIONAMIENTO REAL DE LAB-01
    # ========================================================

    async def provision(
        self,
        username: str,
        challenge_code: str,
        run_id: int,
    ) -> RemoteConnection:
        """
        Para LAB-01:

        1. Busca en Guacamole una conexión SSH existente.
        2. Esa conexión debe apuntar a 192.168.146.137.
        3. La clona para crear una conexión individual.
        4. Concede READ al estudiante.
        5. Devuelve una URL directa /#/client/<id>.
        """

        if challenge_code.upper() != "LAB-01":

            raise GuacamoleApiError(
                f"No existe una configuración de "
                f"acceso remoto para {challenge_code}"
            )

        target_host = "192.168.146.137"
        target_port = "22"

        # --------------------------------------------
        # Buscar conexión base real
        # --------------------------------------------

        connections = await self.list_connections()

        source = None

        for connection in connections:

            hostname = (
                connection.hostname
                or ""
            ).strip()

            protocol = (
                connection.protocol
                or ""
            ).strip().lower()

            port = str(
                connection.port
                or ""
            ).strip()

            if (
                hostname == target_host
                and protocol == "ssh"
                and (
                    port == target_port
                    or port == ""
                )
            ):
                source = connection
                break

        if source is None:

            raise GuacamoleApiError(
                "No existe en Guacamole una conexión "
                "SSH hacia 192.168.146.137:22"
            )

        # --------------------------------------------
        # Nombre único de la conexión
        # --------------------------------------------

        connection_name = (
            f"CTF-{username}-LAB-01-{run_id}"
        )

        # --------------------------------------------
        # Clonar conexión
        # --------------------------------------------

        created = await self.clone_connection(
            source.identifier,
            name=connection_name,
            parent_identifier=(
                source.parent_identifier
                or "ROOT"
            ),
        )

        # --------------------------------------------
        # Conceder únicamente READ
        # --------------------------------------------

        await self.patch_user_permissions(
            username,
            system_permissions=[],
            connection_permissions={
                created.identifier: [
                    "READ"
                ]
            },
        )

        # --------------------------------------------
        # URL directa real
        # --------------------------------------------

        launch_url = await self.direct_connection_url(
            created.identifier
        )

        return RemoteConnection(
            external_reference=connection_name,
            launch_url=launch_url,
        )

    async def revoke(
        self,
        external_reference: str,
    ) -> None:
        """
        La conexión base de la víctima no se elimina.

        La asociación lógica del acceso queda controlada
        por remote_access_assignments/challenge_runs.
        """

        return None

    # ========================================================
    # URL DIRECTA A GUACAMOLE
    # ========================================================

    async def direct_connection_url(
        self,
        identifier: str,
    ) -> str:

        _, data_source = await self._post_token()

        opaque_identifier = base64.b64encode(
            f"{identifier}\x00c\x00{data_source}".encode()
        ).decode()

        return (
            f"{self.base_url}/#/client/"
            f"{opaque_identifier}"
        )


# ============================================================
# FACTORIES
# ============================================================

def make_guacamole_adapter():

    return (
        StubGuacamoleAdapter()
        if get_settings()
        .guacamole_mode
        .lower()
        == "stub"
        else ManagedGuacamoleAdapter()
    )


def make_guacamole_admin():

    return (
        StubGuacamoleAdapter()
        if get_settings()
        .guacamole_mode
        .lower()
        == "stub"
        else ManagedGuacamoleAdapter()
    )