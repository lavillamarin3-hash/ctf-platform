"""Una sesión web activa por usuario (opcional), coordinada en Redis.

Redis es la autoridad; nunca depende solo de localStorage.
La sesión queda bloqueada hasta logout o expiración del token.
"""
from __future__ import annotations

from fastapi import HTTPException


def redis_key(user_id: int | str) -> str:
    return f"auth:one-session:{int(user_id)}"


async def reserve(redis, user_id: int, sid: str, ttl_seconds: int) -> None:
    try:
        acquired = await redis.set(redis_key(user_id), sid, ex=ttl_seconds, nx=True)
    except Exception as exc:
        raise HTTPException(503, "El control de sesiones no está disponible") from exc
    if not acquired:
        raise HTTPException(409, "Esta cuenta ya tiene una sesión activa. Cierra la otra sesión o espera a que expire.")


async def validate(redis, user_id: int, sid: str | None) -> None:
    if not sid:
        raise HTTPException(401, "Inicia una nueva sesión para continuar")
    try:
        active = await redis.get(redis_key(user_id))
    except Exception as exc:
        raise HTTPException(503, "No es posible verificar la sesión") from exc
    if isinstance(active, bytes):
        active = active.decode("utf-8")
    if active != sid:
        raise HTTPException(401, "Esta sesión ya no está activa")


async def release(redis, user_id: int, sid: str | None) -> None:
    if not sid:
        return
    # Eliminación atómica: evita que una sesión anterior borre la nueva.
    script = """if redis.call('GET', KEYS[1]) == ARGV[1] then
                 return redis.call('DEL', KEYS[1]) else return 0 end"""
    try:
        await redis.eval(script, 1, redis_key(user_id), sid)
    except Exception as exc:
        raise HTTPException(503, "No se pudo cerrar la sesión") from exc
