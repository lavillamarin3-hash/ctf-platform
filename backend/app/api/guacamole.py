"""Administración de Apache Guacamole."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import func, select
from ..core import get_settings, require_roles
from ..guacamole import GuacamoleApiError
from ..models import User, VMAsset
from ..services.bootstrap import write_audit
from ..schemas import (
    GuacamoleStatus, GuacamoleUserCreate, GuacamoleUserUpdate, GuacamoleUserView,
    GuacamoleConnectionCreate, GuacamoleConnectionUpdate, GuacamoleConnectionView,
    GuacamolePermissionSet, GuacamolePermissionPatch,
)


from fastapi import APIRouter

router = APIRouter()


def public_parameters(parameters: dict | None) -> dict:
    """Los parámetros técnicos sensibles nunca vuelven al navegador."""
    return {key: value for key, value in (parameters or {}).items()
            if not any(word in key.lower() for word in ("password", "passphrase", "secret", "private-key", "token", "username"))}

@router.get("/api/v1/admin/guacamole/status", response_model=GuacamoleStatus)
async def guacamole_status(request: Request, _=Depends(require_roles("admin"))):
    try:
        result = await request.app.state.guacamole_admin.status()
        result["username"] = "Cuenta de servicio configurada"
        return result
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/v1/admin/guacamole/inventory-audit")
async def guacamole_inventory_audit(request: Request, _=Depends(require_roles("admin"))):
    """Conciliar en solo lectura el inventario CTF con Guacamole remoto.

    NUNCA crea, borra ni modifica conexiones existentes; los identificadores
    de Guacamole pertenecen a su propio servidor y BD independiente.
    """
    if get_settings().guacamole_mode != "real":
        raise HTTPException(status_code=409, detail="Configura GUACAMOLE_MODE=real antes de auditar las conexiones remotas")
    try:
        connections = await request.app.state.guacamole_admin.list_connections()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail="No se pudo consultar el inventario remoto de Guacamole") from exc
    remote = {str(item.identifier): item for item in connections}
    async with request.app.state.session_factory() as session:
        vms = list((await session.scalars(select(VMAsset))).all())
    linked = []
    missing = []
    mismatches = []
    for vm in vms:
        identifier = str(vm.guacamole_connection_id or "").strip()
        if not identifier:
            continue
        item = {"vm_id": vm.id, "vm_name": vm.name, "connection_id": identifier}
        connection = remote.get(identifier)
        if connection is None:
            missing.append(item)
            continue
        linked.append(item)
        if vm.ip_address and connection.hostname and str(vm.ip_address) != str(connection.hostname):
            mismatches.append({**item, "vm_host": vm.ip_address, "remote_host": connection.hostname})
    return {
        "read_only": True, "mode": "real", "remote_connections_total": len(remote),
        "linked_vm_count": len(linked), "missing_vm_connections": missing,
        "host_mismatches": mismatches,
        "unlinked_remote_connections": sum(1 for identifier in remote if identifier not in
            {str(vm.guacamole_connection_id) for vm in vms if vm.guacamole_connection_id}),
        "message": "Inventario remoto consultado. No se crearon ni modificaron conexiones.",
    }


@router.get("/api/v1/admin/guacamole/users", response_model=list[GuacamoleUserView])
async def guacamole_users(request: Request, _=Depends(require_roles("admin"))):
    try:
        users = await request.app.state.guacamole_admin.list_users()
        return [GuacamoleUserView(username=item.username, attributes=item.attributes, last_active=item.last_active)
                for item in users if item.username != get_settings().guacamole_service_account]
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/v1/admin/guacamole/users", response_model=GuacamoleUserView, status_code=status.HTTP_201_CREATED)
async def guacamole_create_user(payload: GuacamoleUserCreate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        created = await request.app.state.guacamole_admin.create_user(
            payload.username, payload.password, email=payload.email, full_name=payload.full_name
        )
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.create", "guacamole_user", payload.username)
            await session.commit()
        return GuacamoleUserView(username=created.username, attributes=created.attributes, last_active=created.last_active)
    except GuacamoleApiError as exc:
        code = 409 if exc.status_code in (400, 409) else 502
        raise HTTPException(status_code=code, detail=exc.detail or str(exc)) from exc


@router.patch("/api/v1/admin/guacamole/users/{username}", response_model=GuacamoleUserView)
async def guacamole_update_user(username: str, payload: GuacamoleUserUpdate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        updated = await request.app.state.guacamole_admin.update_user(
            username, password=payload.password, email=payload.email, full_name=payload.full_name, disabled=payload.disabled
        )
        async with request.app.state.session_factory() as session:
            details = payload.model_dump(exclude_none=True, exclude={"password"})
            details["password_changed"] = payload.password is not None
            await write_audit(session, actor.id, "guacamole.user.update", "guacamole_user", username, details)
            await session.commit()
        return GuacamoleUserView(username=updated.username, attributes=updated.attributes, last_active=updated.last_active)
    except GuacamoleApiError as exc:
        code = 404 if exc.status_code == 404 else 502
        raise HTTPException(status_code=code, detail=exc.detail or str(exc)) from exc


@router.delete("/api/v1/admin/guacamole/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def guacamole_delete_user(username: str, request: Request, actor=Depends(require_roles("admin"))):
    if username == get_settings().guacamole_service_account:
        raise HTTPException(status_code=409, detail="No puedes eliminar la cuenta de servicio de Guacamole")
    async with request.app.state.session_factory() as session:
        linked_user_id = await session.scalar(
            select(User.id).where(func.lower(User.username) == username.lower())
        )
        if linked_user_id is not None:
            raise HTTPException(
                status_code=409,
                detail="Este usuario también existe en CTF. Gestiona la cuenta desde Usuarios y roles para evitar accesos desincronizados.",
            )
    try:
        await request.app.state.guacamole_admin.delete_user(username)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.delete", "guacamole_user", username)
            await session.commit()
    except GuacamoleApiError as exc:
        code = 404 if exc.status_code == 404 else 502
        raise HTTPException(status_code=code, detail=exc.detail or str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/admin/guacamole/connections", response_model=list[GuacamoleConnectionView])
async def guacamole_connections(request: Request, _=Depends(require_roles("admin"))):
    try:
        rows = await request.app.state.guacamole_admin.list_connections()
        return [GuacamoleConnectionView(identifier=x.identifier, name=x.name, protocol=x.protocol, parent_identifier=x.parent_identifier, hostname=x.hostname, port=x.port, parameters=public_parameters(x.parameters), remote_username=(x.parameters or {}).get('username'), attributes=x.attributes or {}, active_connections=x.active_connections) for x in rows]
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=exc.detail or str(exc)) from exc


@router.post("/api/v1/admin/guacamole/connections", response_model=GuacamoleConnectionView, status_code=status.HTTP_201_CREATED)
async def guacamole_create_connection(payload: GuacamoleConnectionCreate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        c = await request.app.state.guacamole_admin.create_connection(name=payload.name, protocol=payload.protocol, hostname=payload.hostname, port=payload.port, username=payload.username, password=payload.password, domain=payload.domain, parent_identifier=payload.parent_identifier)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.create", "guacamole_connection", c.identifier, {"name": c.name, "protocol": c.protocol, "hostname": c.hostname, "port": c.port}); await session.commit()
        return GuacamoleConnectionView(identifier=c.identifier, name=c.name, protocol=c.protocol, parent_identifier=c.parent_identifier, hostname=c.hostname, port=c.port, parameters=public_parameters(c.parameters), remote_username=(c.parameters or {}).get('username'), attributes=c.attributes or {}, active_connections=c.active_connections)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=409 if exc.status_code in (400,409) else 502, detail=exc.detail or str(exc)) from exc


@router.put("/api/v1/admin/guacamole/connections/{identifier}", response_model=GuacamoleConnectionView)
async def guacamole_update_connection(identifier: str, payload: GuacamoleConnectionUpdate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        c = await request.app.state.guacamole_admin.update_connection(identifier, name=payload.name, protocol=payload.protocol, hostname=payload.hostname, port=payload.port, username=payload.username, password=payload.password, domain=payload.domain, parent_identifier=payload.parent_identifier)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.update", "guacamole_connection", identifier, {"name": c.name, "protocol": c.protocol, "hostname": c.hostname, "port": c.port}); await session.commit()
        return GuacamoleConnectionView(identifier=c.identifier, name=c.name, protocol=c.protocol, parent_identifier=c.parent_identifier, hostname=c.hostname, port=c.port, parameters=public_parameters(c.parameters), remote_username=(c.parameters or {}).get('username'), attributes=c.attributes or {}, active_connections=c.active_connections)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc


@router.delete("/api/v1/admin/guacamole/connections/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def guacamole_delete_connection(identifier: str, request: Request, actor=Depends(require_roles("admin"))):
    try:
        await request.app.state.guacamole_admin.delete_connection(identifier)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.delete", "guacamole_connection", identifier); await session.commit()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/v1/admin/guacamole/connections/{identifier}/check")
async def guacamole_check_connection(identifier: str, request: Request, actor=Depends(require_roles("admin"))):
    """Comprobar conectividad TCP, sin prometer autenticación remota."""
    from ..services.guacamole_preflight import check_connection
    try:
        matches = await request.app.state.guacamole_admin.list_connections()
        connection = next((c for c in matches if c.identifier == identifier), None)
        if connection is None:
            raise HTTPException(status_code=404, detail="Conexión no encontrada")
        result = await check_connection(connection)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.preflight", "guacamole_connection", identifier,
                              {"reachable": result["reachable"], "host": result["hostname"], "port": result["port"]})
            await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail="No fue posible consultar Guacamole") from exc


@router.get("/api/v1/admin/guacamole/users/{username}/permissions", response_model=GuacamolePermissionSet)
async def guacamole_get_permissions(username: str, request: Request, _=Depends(require_roles("admin"))):
    if username == get_settings().guacamole_service_account:
        data = {"systemPermissions": ["ADMINISTER"], "connectionPermissions": {}}
    else:
        try: data = await request.app.state.guacamole_admin.get_user_permissions(username)
        except GuacamoleApiError as exc: raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc
    return GuacamolePermissionSet(system_permissions=list(data.get("systemPermissions") or []), connection_permissions={str(k): list(v or []) for k,v in (data.get("connectionPermissions") or {}).items()})


@router.patch("/api/v1/admin/guacamole/users/{username}/permissions", response_model=GuacamolePermissionSet)
async def guacamole_patch_permissions(username: str, payload: GuacamolePermissionPatch, request: Request, actor=Depends(require_roles("admin"))):
    if username == get_settings().guacamole_service_account:
        raise HTTPException(status_code=409, detail="La cuenta de servicio no puede ser administrada desde el panel")
    allowed_system = {"ADMINISTER", "CREATE_CONNECTION", "CREATE_CONNECTION_GROUP", "CREATE_SHARING_PROFILE", "CREATE_USER", "CREATE_USER_GROUP"}
    allowed_object = {"READ", "UPDATE", "DELETE", "ADMINISTER"}
    if any(x not in allowed_system for x in payload.system_permissions) or any(x not in allowed_object for values in payload.connection_permissions.values() for x in values):
        raise HTTPException(status_code=422, detail="Permiso de Guacamole no válido")
    try:
        data = await request.app.state.guacamole_admin.patch_user_permissions(username, system_permissions=payload.system_permissions, connection_permissions=payload.connection_permissions)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.permissions", "guacamole_user", username, {"system_permissions": payload.system_permissions, "connection_permissions": payload.connection_permissions}); await session.commit()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc
    return GuacamolePermissionSet(system_permissions=list(data.get("systemPermissions") or []), connection_permissions={str(k): list(v or []) for k,v in (data.get("connectionPermissions") or {}).items()})


