"""Notificaciones de ranking por Redis pub/sub, autenticadas por ticket."""
import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response, WebSocket
from .auth import current
from ..persistence.models import User
from ..persistence.repository import now

router = APIRouter(prefix="/api/v1")


@router.post("/ranking/ticket")
async def ticket(request: Request, response: Response, user=Depends(current)):
    runtime = request.app.state.runtime
    value = await runtime.cache.ticket("ranking", user.id, request.state.jwt)
    response.set_cookie("ctf-ranking", value, max_age=45, path="/api/v1/ranking/ws", httponly=True, samesite="strict", secure=runtime.settings.public_origin.startswith("https://"))
    return {"ok": True}


@router.websocket("/ranking/ws")
async def events(browser: WebSocket):
    runtime = browser.app.state.runtime
    if browser.headers.get("origin") != runtime.settings.public_origin:
        await browser.close(code=1008)
        return
    try:
        ticket = await runtime.cache.consume(browser.cookies.get("ctf-ranking", ""))
        if not ticket or ticket[0] != "ranking": raise ValueError()
        _, uid, claims = ticket
        await browser.accept()
        async with runtime.cache.client.pubsub() as subscription:
            await subscription.subscribe("ws:canal:ranking")
            async def pump():
                while True:
                    if claims["exp"] <= now().timestamp() or await runtime.cache.client.exists(f"jwt:revocado:{claims['jti']}"): return
                    async with runtime.repo.sessions() as s:
                        user = await s.get(User, UUID(uid))
                        if not user or user.state != "activo" or user.must_change_password or user.token_version != claims.get("ver"): return
                    message = await subscription.get_message(ignore_subscribe_messages=True, timeout=5)
                    if message: await browser.send_json({"event": "ranking.updated"})
                    await asyncio.sleep(0.2)
            async def disconnected():
                while True: await browser.receive_text()
            tasks = [asyncio.create_task(pump()), asyncio.create_task(disconnected())]
            try: await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks: task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except Exception: pass
    finally:
        try: await browser.close()
        except Exception: pass
