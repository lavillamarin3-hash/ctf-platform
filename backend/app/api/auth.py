"""Autenticación, sesión y salud del servicio."""

from __future__ import annotations

from datetime import timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from ..core import create_token, get_current_user, get_settings, hash_password, require_roles, verify_password
from ..models import User
from ..schemas import LoginRequest, PasswordChange, ProfileUpdate, TokenResponse, UserView
from ..services.bootstrap import check_rate_limit, write_audit


from fastapi import APIRouter

router = APIRouter()

async def health() -> dict:
    return {"status": "ok", "service": "ctf-api"}


@router.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request):
    await check_rate_limit(request.app.state.redis, f"rate:login:{payload.username}", maximum=10)
    async with request.app.state.session_factory() as session:
        user = await session.scalar(select(User).where(User.username == payload.username))
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
        await write_audit(session, user.id, "auth.login", "user", str(user.id))
        await session.commit()
    token = create_token(str(user.id), "access", timedelta(minutes=get_settings().access_token_minutes))
    return TokenResponse(access_token=token, user=UserView.model_validate(user))


@router.get("/api/v1/auth/me", response_model=UserView)
async def me(user=Depends(get_current_user)):
    return UserView.model_validate(user)

@router.patch("/api/v1/auth/profile", response_model=UserView)
async def update_profile(payload: ProfileUpdate, request: Request, actor=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, actor.id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        username = payload.username.strip()
        existing = await session.scalar(select(User).where(User.username == username, User.id != actor.id))
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre")
        if payload.email:
            existing_email = await session.scalar(select(User).where(User.email == payload.email, User.id != actor.id))
            if existing_email:
                raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
        target.username = username
        target.email = payload.email
        await write_audit(session, actor.id, "profile.update", "user", str(actor.id), {"fields": ["username", "email"]})
        await session.commit()
        await session.refresh(target)
        return UserView.model_validate(target)

@router.post("/api/v1/auth/password")
async def change_password(payload: PasswordChange, request: Request, actor=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, actor.id)
        if target is None or not verify_password(payload.current_password, target.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
        target.password_hash = hash_password(payload.new_password)
        await write_audit(session, actor.id, "profile.password_change", "user", str(actor.id))
        await session.commit()
    return {"ok": True}


