"""Administración remota sin migraciones ni acceso al esquema histórico."""
import asyncio
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr, field_validator
from app.guacamole import GuacamoleApiError
from app.services.guacamole_preflight import LAB_TARGETS, ALLOWED_PORTS, connection_target, check_connection
from .auth import roles
from ..persistence.repository import audit

router = APIRouter(prefix="/api/v1/admin/guacamole", dependencies=[Depends(roles(1))])


class ConnectionInput(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    hostname: str
    protocol: Literal["ssh", "rdp"] = "ssh"
    port: int = Field(ge=1, le=65535)
    username: str | None = Field(default=None, max_length=100)
    password: SecretStr | None = None
    domain: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def name_allowed(cls, value):
        value = value.strip()
        if len(value) < 3 or value.lower().startswith("ctf_"):
            raise ValueError("Nombre reservado para corridas")
        return value


class DeleteInput(BaseModel):
    confirmation: str


class UserInput(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,49}$")
    password: SecretStr = Field(min_length=10, max_length=200)


class AccessInput(BaseModel):
    connections: list[str] = Field(max_length=100)


async def remote(operation):
    try:
        async with asyncio.timeout(25):
            return await operation
    except (GuacamoleApiError, TimeoutError, OSError):
        raise HTTPException(502, "No se pudo completar la operación en Guacamole. Actualiza el inventario antes de repetirla.") from None


def connection_view(item):
    # Lista cerrada: nunca devolver parámetros, contraseñas, claves o tokens.
    try:
        connection_target(item)
        supported = True
    except ValueError:
        supported = False
    return {"identifier": item.identifier, "name": item.name, "protocol": item.protocol,
            "hostname": item.hostname, "port": item.port, "active_connections": item.active_connections,
            "username": (item.parameters or {}).get("username", ""),
            "domain": (item.parameters or {}).get("domain", ""),
            "protected": item.name.lower().startswith("ctf_"), "supported": supported}


async def record(request, action, identifier):
    async with request.app.state.runtime.repo.sessions.begin() as session:
        audit(session, action, identifier, request.state.user_id)


async def find(request, identifier, *, mutable=False):
    rows = await remote(request.app.state.runtime.guacamole.list_connections())
    item = next((row for row in rows if row.identifier == identifier), None)
    if not item:
        raise HTTPException(404, "Conexión no encontrada. Actualiza el inventario.")
    if mutable and (item.name.lower().startswith("ctf_") or item.active_connections):
        raise HTTPException(409, "La conexión pertenece a una corrida o tiene sesiones abiertas.")
    return item


def target(item):
    try:
        connection_target(item)
    except ValueError:
        raise HTTPException(422, "Selecciona una máquina y un puerto autorizados del laboratorio.") from None


def protect_user(request, username):
    if username.lower().startswith("ctf_") or username == request.app.state.runtime.settings.guacamole_admin_user:
        raise HTTPException(409, "La cuenta técnica y las cuentas de corrida se gestionan automáticamente.")


@router.get("/inventory")
async def inventory(request: Request):
    adapter = request.app.state.runtime.guacamole
    connections = await remote(adapter.list_connections())
    users = await remote(adapter.list_users())
    service = request.app.state.runtime.settings.guacamole_admin_user
    return {"verified": True, "connections": [connection_view(c) for c in connections],
            "users": [{"username": u.username, "disabled": u.attributes.get("disabled") == "true",
                       "protected": u.username == service or u.username.lower().startswith("ctf_")} for u in users],
            "targets": [{"hostname": ip, "name": name} for ip, name in LAB_TARGETS.items()],
            "ports": {p: sorted(values) for p, values in ALLOWED_PORTS.items()}}


@router.post("/connections", status_code=201)
async def create_connection(body: ConnectionInput, request: Request):
    target(body)
    adapter = request.app.state.runtime.guacamole
    existing = await remote(adapter.list_connections())
    if any(c.name.casefold() == body.name.casefold() for c in existing):
        raise HTTPException(409, "Ya existe una conexión con ese nombre.")
    data = body.model_dump(exclude={"password"})
    data["password"] = body.password.get_secret_value() if body.password else None
    item = await remote(adapter.create_connection(**data))
    await record(request, "guacamole.connection.created", item.identifier)
    return connection_view(item)


@router.put("/connections/{identifier}")
async def update_connection(identifier: str, body: ConnectionInput, request: Request):
    target(body)
    current = await find(request, identifier, mutable=True)
    target(current)
    adapter = request.app.state.runtime.guacamole
    rows = await remote(adapter.list_connections())
    if any(c.identifier != identifier and c.name.casefold() == body.name.casefold() for c in rows):
        raise HTTPException(409, "Ya existe una conexión con ese nombre.")
    data = body.model_dump(exclude={"password"})
    # Vacío conserva la credencial remota. El cliente existente fusiona parámetros.
    data["password"] = body.password.get_secret_value() if body.password and body.password.get_secret_value() else None
    item = await remote(adapter.update_connection(identifier, parent_identifier=current.parent_identifier, **data))
    await record(request, "guacamole.connection.updated", identifier)
    return connection_view(item)


@router.delete("/connections/{identifier}")
async def delete_connection(identifier: str, body: DeleteInput, request: Request):
    item = await find(request, identifier, mutable=True)
    target(item)
    if body.confirmation != item.name:
        raise HTTPException(422, "Escribe el nombre exacto de la conexión.")
    await remote(request.app.state.runtime.guacamole.delete_connection(identifier))
    await record(request, "guacamole.connection.deleted", identifier)
    return {"ok": True}


@router.post("/connections/{identifier}/check")
async def test_connection(identifier: str, request: Request):
    item = await find(request, identifier)
    target(item)
    result = await check_connection(item)
    await record(request, "guacamole.connection.checked", identifier)
    # No cambiar disponibilidad de máquinas, pilotos ni laboratorios.
    return result


@router.post("/users", status_code=201)
async def create_user(body: UserInput, request: Request):
    protect_user(request, body.username)
    users = await remote(request.app.state.runtime.guacamole.list_users())
    if any(u.username.casefold() == body.username.casefold() for u in users):
        raise HTTPException(409, "La cuenta ya existe en Guacamole.")
    await remote(request.app.state.runtime.guacamole.create_user(body.username, body.password.get_secret_value()))
    await record(request, "guacamole.user.created", body.username)
    return {"username": body.username}


@router.get("/users/{username}/access")
async def user_access(username: str, request: Request):
    protect_user(request, username)
    permissions = await remote(request.app.state.runtime.guacamole.get_user_permissions(username))
    return {"connections": [cid for cid, values in permissions["connectionPermissions"].items() if "READ" in values],
            "administrator": "ADMINISTER" in permissions["systemPermissions"]}


@router.put("/users/{username}/access")
async def update_access(username: str, body: AccessInput, request: Request):
    protect_user(request, username)
    adapter = request.app.state.runtime.guacamole
    rows = await remote(adapter.list_connections())
    editable = {c.identifier for c in rows if not c.name.lower().startswith("ctf_") and connection_view(c)["supported"]}
    if set(body.connections) - editable:
        raise HTTPException(422, "Solo puedes asignar conexiones permanentes del laboratorio.")
    previous = await remote(adapter.get_user_permissions(username))
    if "ADMINISTER" in previous["systemPermissions"]:
        raise HTTPException(409, "Esta cuenta ya administra Guacamole. Sus permisos globales se revisan en el servidor.")
    permissions = {cid: list(values) for cid, values in previous["connectionPermissions"].items()}
    for cid in editable:
        values = [p for p in permissions.get(cid, []) if p != "READ"]
        if cid in body.connections: values.append("READ")
        permissions[cid] = values
    await remote(adapter.patch_user_permissions(username, system_permissions=previous["systemPermissions"], connection_permissions=permissions))
    await record(request, "guacamole.user.access", username)
    return {"ok": True}
