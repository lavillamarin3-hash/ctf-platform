"""Puente WebSocket autenticado entre un run autorizado y Apache Guacamole."""

from __future__ import annotations

import asyncio
from typing import Literal
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Body, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from websockets.asyncio.client import connect

from ..core import get_settings, now_utc, require_roles
from ..models import Challenge, ChallengeInstance, ChallengeRun, User, VMAsset
from ..domain.instances.states import InstanceState
from ..services.challenge_runtime import _find_challenge_vm, _resolve_guacamole_connection
from ..services.bootstrap import check_rate_limit
from .runs import _assigned

router = APIRouter()


class TerminalLogin(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class TerminalSelection(BaseModel):
    protocol: Literal["ssh", "rdp"]


def _same_host(first: str | None, second: str | None) -> bool:
    return bool(first and second and first.strip().casefold() == second.strip().casefold())


async def _protocol_targets(app, vm: VMAsset | None, primary_id: str) -> dict[str, str]:
    """Solo conexiones Guacamole de la VM reservada; nunca IDs enviados por el cliente."""
    try:
        connections = await app.state.guacamole_admin.list_connections()
    except Exception as exc:
        raise HTTPException(503, "No se pudieron comprobar las conexiones del laboratorio") from exc
    targets: dict[str, str] = {}
    for connection in connections:
        protocol = (connection.protocol or "").strip().lower()
        if protocol not in {"ssh", "rdp"}:
            continue
        if str(connection.identifier) == primary_id:
            targets[protocol] = primary_id
        elif vm and _same_host(connection.hostname, vm.ip_address):
            targets.setdefault(protocol, str(connection.identifier))
    return targets


async def authorized_target(app, run_id: int, user_id: int, protocol: str | None = None):
    """El destino proviene de la instancia reservada, nunca del navegador."""
    async with app.state.session_factory() as session:
        user = await session.get(User, user_id)
        run = await session.get(ChallengeRun, run_id)
        if user is None or user.role != "player" or not user.is_active or run is None or run.user_id != user_id:
            raise HTTPException(404, "Laboratorio no encontrado")
        if run.status != "active" or run.expires_at <= now_utc():
            raise HTTPException(409, "El laboratorio está cerrado o ha expirado")
        challenge = await session.get(Challenge, run.challenge_id)
        if challenge is None or not challenge.is_published or not await _assigned(session, challenge.id, user_id):
            raise HTTPException(403, "Este laboratorio ya no está asignado a tu grupo")
        instance = await session.scalar(select(ChallengeInstance).where(ChallengeInstance.run_id == run.id))
        vm = None
        if instance:
            if instance.user_id != user_id or instance.state != InstanceState.IN_USE.value or not instance.guacamole_connection_id:
                raise HTTPException(409, "La instancia no está disponible para tu sesión")
            connection_id = instance.guacamole_connection_id
            if protocol:
                vm = await session.get(VMAsset, instance.vm_asset_id)
        else:
            _, vm = await _find_challenge_vm(session, challenge)
            connection = await _resolve_guacamole_connection(AppRequest(app), vm) if vm else None
            if not connection:
                raise HTTPException(409, "Este reto no dispone de conexión remota")
            connection_id = connection.identifier
        if protocol:
            targets = await _protocol_targets(app, vm, str(connection_id))
            if protocol not in targets:
                raise HTTPException(409, "Esta conexión no está configurada para la VM asignada")
            connection_id = targets[protocol]
        return str(connection_id), run.expires_at, user.username


class AppRequest:
    def __init__(self, app):
        self.app = app


def tunnel_url(base_url: str, delegated: dict, connection_id: str, params) -> str:
    parts = urlsplit(base_url)
    if parts.scheme not in ("http", "https") or parts.username or parts.password:
        raise ValueError("URL de Guacamole no válida")
    query = {
        "token": delegated["token"], "GUAC_DATA_SOURCE": delegated["data_source"],
        "GUAC_ID": connection_id, "GUAC_TYPE": "c",
        "GUAC_WIDTH": str(max(320, min(int(params.get("width", "1200")), 3840))),
        "GUAC_HEIGHT": str(max(240, min(int(params.get("height", "720")), 2160))),
        "GUAC_DPI": "96", "GUAC_TIMEZONE": "UTC",
    }
    scheme = "wss" if parts.scheme == "https" else "ws"
    return urlunsplit((scheme, parts.netloc, parts.path.rstrip("/") + "/websocket-tunnel", urlencode(query), ""))


@router.get("/api/v1/terminal/client.js")
async def terminal_client(request: Request):
    adapter = request.app.state.guacamole
    if not hasattr(adapter, "client_library"):
        raise HTTPException(503, "La terminal requiere Guacamole real")
    cached = getattr(request.app.state, "guacamole_client_library", None)
    if cached is None:
        try:
            cached = await adapter.client_library()
        except Exception as exc:
            raise HTTPException(503, "No se pudo cargar el cliente de la terminal") from exc
        request.app.state.guacamole_client_library = cached
    return Response(cached, media_type="application/javascript", headers={"Cache-Control": "public, max-age=3600"})


@router.post("/api/v1/terminal/auth")
async def terminal_auth(payload: TerminalLogin, request: Request, user=Depends(require_roles("player"))):
    await check_rate_limit(request.app.state.redis, f"rate:terminal:auth:{user.id}", maximum=5)
    try:
        delegated = await request.app.state.guacamole.authenticate_player(user.username, payload.password)
        await request.app.state.terminal_sessions.remember_user(user.id, delegated)
    except Exception as exc:
        raise HTTPException(401, "No se pudo conectar con tu cuenta de laboratorio. Revisa tu contraseña o consulta al instructor.") from exc
    return {"ready": True}


@router.get("/api/v1/runs/{run_id}/terminal/options")
async def terminal_options(run_id: int, request: Request, user=Depends(require_roles("player"))):
    primary_id, _, _ = await authorized_target(request.app, run_id, user.id)
    async with request.app.state.session_factory() as session:
        run = await session.get(ChallengeRun, run_id)
        instance = await session.scalar(select(ChallengeInstance).where(ChallengeInstance.run_id == run.id))
        if instance:
            vm = await session.get(VMAsset, instance.vm_asset_id)
        else:
            challenge = await session.get(Challenge, run.challenge_id)
            _, vm = await _find_challenge_vm(session, challenge)
    targets = await _protocol_targets(request.app, vm, primary_id)
    return {"protocols": [name for name in ("ssh", "rdp") if name in targets]}


@router.post("/api/v1/runs/{run_id}/terminal/session")
async def terminal_session(run_id: int, request: Request, response: Response, user=Depends(require_roles("player")), selection: TerminalSelection | None = Body(default=None)):
    await check_rate_limit(request.app.state.redis, f"rate:terminal:session:{user.id}", maximum=12)
    protocol = selection.protocol if selection else None
    if protocol:
        _, expires_at, _ = await authorized_target(request.app, run_id, user.id, protocol)
    else:
        _, expires_at, _ = await authorized_target(request.app, run_id, user.id)
    sessions = request.app.state.terminal_sessions
    if not await sessions.get_user(user.id):
        raise HTTPException(428, "Conecta con tu cuenta de laboratorio para abrir la terminal.")
    try:
        if protocol:
            ticket = await sessions.issue(run_id, user.id, protocol)
        else:
            ticket = await sessions.issue(run_id, user.id)
    except ValueError as exc:
        raise HTTPException(409, "El laboratorio se está cerrando") from exc
    cookie_path = f"/api/v1/runs/{run_id}/terminal"
    response.set_cookie(f"ctf-terminal-{run_id}", ticket, max_age=60, path=cookie_path,
                        httponly=True, secure=get_settings().public_origin.startswith("https://"), samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    return {"websocket_path": f"{cookie_path}/ws", "expires_at": expires_at}


async def bridge(app, run_id: int, user_id: int, browser: WebSocket, upstream):
    async def browser_to_guac():
        while True:
            data = await browser.receive_text()
            if len(data) > 1_000_000:
                raise ValueError("Mensaje de terminal demasiado grande")
            await upstream.send(data)

    async def guac_to_browser():
        async for data in upstream:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await browser.send_text(data)

    async def watch_run():
        while True:
            await asyncio.sleep(1)
            if await app.state.terminal_sessions.is_closed(run_id):
                return
            if not await app.state.terminal_sessions.get_user(user_id):
                return
            await authorized_target(app, run_id, user_id)

    tasks = [asyncio.create_task(coro()) for coro in (browser_to_guac, guac_to_browser, watch_run)]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@router.websocket("/api/v1/runs/{run_id}/terminal/ws")
async def terminal_websocket(run_id: int, websocket: WebSocket):
    # No acepta JWT/tokens en la URL. El ticket HttpOnly dura un minuto y se consume una vez.
    if websocket.headers.get("origin") != get_settings().public_origin.rstrip("/"):
        await websocket.close(code=1008)
        return
    sessions = websocket.app.state.terminal_sessions
    try:
        ticket = await sessions.consume(websocket.cookies.get(f"ctf-terminal-{run_id}"), run_id)
        if not ticket:
            await websocket.close(code=1008)
            return
        protocol = ticket.get("protocol")
        if protocol:
            connection_id, _, username = await authorized_target(websocket.app, run_id, ticket["user_id"], protocol)
        else:
            connection_id, _, username = await authorized_target(websocket.app, run_id, ticket["user_id"])
        delegated = await sessions.get_user(ticket["user_id"])
        if not delegated or delegated["username"] != username:
            await websocket.close(code=1008)
            return
        adapter = websocket.app.state.guacamole
        url = tunnel_url(adapter.base_url, delegated, connection_id, websocket.query_params)
        await websocket.accept(subprotocol="guacamole" if "guacamole" in websocket.scope.get("subprotocols", []) else None)
        async with connect(url, subprotocols=["guacamole"], open_timeout=15, max_size=8_000_000) as upstream:
            if await sessions.is_closed(run_id):
                return
            sessions.connections.setdefault(run_id, set()).add(upstream)
            try:
                await bridge(websocket.app, run_id, ticket["user_id"], websocket, upstream)
            finally:
                sessions.connections.get(run_id, set()).discard(upstream)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        # Nunca registrar la URL upstream: contiene el token personal de Guacamole.
        try:
            await websocket.close(code=1011, reason="No se pudo mantener la conexión del laboratorio")
        except Exception:
            pass
    finally:
        try:
            await websocket.close(code=1000)
        except Exception:
            pass
