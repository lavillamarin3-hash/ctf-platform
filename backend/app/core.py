from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import hmac
import os
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ctf_platform:ctf_platform@localhost:5432/ctf_platform"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "unsafe-development-secret-change-me"
    field_hmac_secret: str = "unsafe-development-hmac-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 20
    refresh_token_days: int = 7
    ctf_demo_password: str = "LabDemo-ChangeMe-2026!"
    ctf_seed_demo_data: bool = True
    guacamole_mode: str = "stub"
    guacamole_base_url: str = "https://guacamole.lab"
    guacamole_api_url: str | None = None
    guacamole_service_account: str | None = None
    guacamole_service_password: str | None = None
    public_origin: str = "http://localhost:8081"


@lru_cache
def get_settings() -> Settings:
    return Settings()


password_hasher = PasswordHasher()
bearer_scheme = HTTPBearer(auto_error=False)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(value: str) -> str:
    return password_hasher.hash(value)


def verify_password(value: str, value_hash: str) -> bool:
    try:
        return password_hasher.verify(value_hash, value)
    except (VerifyMismatchError, InvalidHashError):
        return False


def submission_fingerprint(value: str) -> str:
    secret = get_settings().field_hmac_secret.encode()
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


def create_token(subject: str, token_type: str, expires: timedelta) -> str:
    settings = get_settings()
    issued = now_utc()
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": issued,
        "exp": issued + expires,
        "iss": "lab-ctf-platform",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str = "access") -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], issuer="lab-ctf-platform")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o vencida") from exc
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de sesión inválido")
    return payload


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación requerida")
    payload = decode_token(credentials.credentials)
    session_factory = request.app.state.session_factory
    from .models import User
    from sqlalchemy import select

    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.id == int(payload["sub"])))
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no disponible")
        return user


def require_roles(*roles: str):
    async def dependency(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para esta acción")
        return user
    return dependency

