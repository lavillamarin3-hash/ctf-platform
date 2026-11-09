import asyncio
from uuid import UUID
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket
from websockets.asyncio.client import connect
from sqlalchemy import select
from .auth import current
from ..persistence.models import Run, User, Member, Assignment, Challenge
from ..persistence.repository import now
from ...domain.laboratory import State

router = APIRouter(prefix="/api/v1")


async def authorized(runtime, run_id, user_id, claims=None):
    async with runtime.repo.sessions() as s:
        run = await s.get(Run, run_id)
        user = await s.get(User, UUID(str(user_id)))
        if not user or user.state != "activo" or user.must_change_password or not run or str(run.user_id) != str(user_id) or run.state != State.ACTIVE or run.expires <= now():
            raise HTTPException(403, "Terminal no disponible")
        if claims and user.token_version != claims.get("ver"): raise HTTPException(403, "Sesión terminada")
        assigned = await s.scalar(select(Member.id).join(Assignment, Assignment.group_id == Member.group_id).join(Challenge, Challenge.id == Assignment.challenge_id).where(Member.user_id == user.id, Challenge.id == run.challenge_id, Challenge.state == "published").limit(1))
        if not assigned: raise HTTPException(403, "Reto no asignado")
        return run


@router.get("/terminal/client.js")
async def library(request: Request):
    source = await request.app.state.runtime.guacamole.client_library()
    return Response(source, media_type="text/javascript", headers={"Cache-Control": "private, max-age=3600"})


@router.post("/runs/{run_id}/terminal")
async def ticket(run_id: str, request: Request, response: Response, user=Depends(current)):
    runtime = request.app.state.runtime
    await authorized(runtime, run_id, user.id)
    value = await runtime.cache.ticket(run_id, user.id, request.state.jwt)
    path = f"/api/v1/runs/{run_id}/terminal"
    response.set_cookie("ctf-terminal", value, max_age=45, path=path, httponly=True, secure=runtime.settings.public_origin.startswith("https://"), samesite="strict")
    return {"path": path + "/ws"}


@router.websocket("/runs/{run_id}/terminal/ws")
async def terminal(run_id: str, browser: WebSocket):
    runtime = browser.app.state.runtime
    if browser.headers.get("origin") != runtime.settings.public_origin:
        await browser.close(code=1008)
        return
    try:
        ticket = await runtime.cache.consume(browser.cookies.get("ctf-terminal", ""))
        if not ticket or ticket[0] != run_id: raise ValueError()
        _, user_id, claims = ticket
        run = await authorized(runtime, run_id, user_id, claims)
        async def check_token():
            if claims["exp"] <= now().timestamp() or await runtime.cache.client.exists(f"jwt:revocado:{claims['jti']}"): raise ValueError()
        await check_token()
        delegated = await runtime.guacamole.session(run_id)
        query = urlencode({"token": delegated["token"], "GUAC_DATA_SOURCE": delegated["data_source"], "GUAC_ID": run.connection_id,
                           "GUAC_TYPE": "c", "GUAC_WIDTH": "1100", "GUAC_HEIGHT": "650", "GUAC_DPI": "96"})
        url = runtime.guacamole.base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/websocket-tunnel?" + query
        await browser.accept(subprotocol="guacamole")
        async with connect(url, subprotocols=["guacamole"], open_timeout=10, max_size=4_000_000) as upstream:
            async def send():
                while True:
                    data = await browser.receive_text()
                    if len(data) > 1_000_000: raise ValueError()
                    await upstream.send(data)
            async def receive():
                async for data in upstream:
                    await browser.send_text(data.decode() if isinstance(data, bytes) else data)
            async def watch():
                while True:
                    await asyncio.sleep(2)
                    await check_token()
                    await authorized(runtime, run_id, user_id, claims)
            tasks = [asyncio.create_task(f()) for f in (send, receive, watch)]
            try:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks: task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        # Sin URL upstream ni excepciones del proveedor: contienen tokens.
        pass
    finally:
        try: await browser.close(code=1000)
        except Exception: pass
