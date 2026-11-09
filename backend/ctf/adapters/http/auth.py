from datetime import timedelta
from uuid import UUID
import secrets
import jwt
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy import select
from .schemas import Login, Password
from ...application.admin import hasher
from ..persistence.models import User
from ..persistence.repository import now, audit

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def user_view(user):
    return {"id": str(user.id), "username": user.username, "role": user.role, "must_change_password": user.must_change_password}


def issue_token(runtime, user):
    return jwt.encode({"sub": str(user.id), "ver": user.token_version, "jti": secrets.token_hex(16), "iss": "cociber-fresh", "iat": now(), "exp": now() + timedelta(minutes=runtime.settings.jwt_expira_minutos)}, runtime.settings.jwt_secret.get_secret_value(), algorithm="HS256")


def password_matches(value, hashed):
    try: return hasher.verify(hashed, value)
    except (VerificationError, InvalidHashError): return False


async def current(request: Request, credential=Depends(bearer)):
    if not credential: raise HTTPException(401, "Autenticación requerida")
    runtime = request.app.state.runtime
    try:
        payload = jwt.decode(credential.credentials, runtime.settings.jwt_secret.get_secret_value(), algorithms=["HS256"], issuer="cociber-fresh", options={"require": ["sub", "exp", "jti", "iat"]})
        if await runtime.cache.client.exists(f"jwt:revocado:{payload['jti']}"): raise ValueError()
        user_id = UUID(payload["sub"])
    except jwt.PyJWTError: raise HTTPException(401, "Sesión inválida o vencida") from None
    except ValueError: raise HTTPException(401, "Sesión inválida o vencida") from None
    async with runtime.repo.sessions() as s:
        user = await s.get(User, user_id)
        if not user or user.state != "activo" or user.token_version != payload.get("ver"): raise HTTPException(401, "Usuario o sesión no disponible")
        if user.must_change_password and request.url.path not in ("/api/v1/auth/me", "/api/v1/auth/password", "/api/v1/auth/logout"):
            raise HTTPException(403, "Cambia la contraseña inicial para continuar")
        request.state.user_id = user.id
        request.state.jwt = payload
        return user


def roles(*allowed):
    async def dependency(user=Depends(current)):
        if user.role not in allowed: raise HTTPException(403, "No tienes permiso para esta acción")
        return user
    return dependency


@router.post("/auth/login")
async def login(body: Login, request: Request):
    runtime = request.app.state.runtime
    if not await runtime.cache.login_attempt(body.username): raise HTTPException(429, "Demasiados intentos. Espera un minuto.")
    async with runtime.repo.sessions.begin() as s:
        user = await s.scalar(select(User).where(User.username == body.username))
        valid = password_matches(body.password, user.password_hash if user else DUMMY_HASH)
        if not valid or not user or user.state != "activo":
            audit(s, "auth.failure", "login")
        else:
            audit(s, "auth.login", user.id, user.id)
    if not valid or not user or user.state != "activo": raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = issue_token(runtime, user)
    return {"access_token": token, "user": user_view(user)}


@router.get("/auth/me")
async def me(user=Depends(current)): return user_view(user)


@router.post("/auth/password")
async def change_password(body: Password, request: Request, user=Depends(current)):
    runtime = request.app.state.runtime
    if not password_matches(body.current, user.password_hash) or body.current == body.new:
        raise HTTPException(422, "Revisa la contraseña actual y elige una nueva diferente")
    async with runtime.repo.sessions.begin() as s:
        target = await s.scalar(select(User).where(User.id == user.id).with_for_update())
        if not password_matches(body.current, target.password_hash): raise HTTPException(409, "La contraseña cambió; inicia sesión de nuevo")
        target.password_hash, target.must_change_password = hasher.hash(body.new), False
        target.token_version += 1
        audit(s, "auth.password_changed", user.id, user.id)
    return {"ok": True, "access_token": issue_token(runtime, target), "user": user_view(target)}


@router.post("/auth/logout")
async def logout(request: Request, user=Depends(current)):
    payload = request.state.jwt
    await request.app.state.runtime.cache.client.set(f"jwt:revocado:{payload['jti']}", "1", ex=max(1, int(payload["exp"] - now().timestamp())))
    return {"ok": True}
