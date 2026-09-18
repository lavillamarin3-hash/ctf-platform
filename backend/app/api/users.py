"""Administración de usuarios y roles."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import func, select
from ..core import get_current_user, require_roles, hash_password
from ..guacamole import GuacamoleApiError
from ..models import User
from ..schemas import UserCreate, UserUpdate, UserView
from ..services.bootstrap import write_audit


from fastapi import APIRouter

router = APIRouter()

@router.get("/api/v1/users", response_model=list[UserView])
async def list_users(request: Request, _=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        users = (await session.scalars(select(User).order_by(User.username))).all()
        return [UserView.model_validate(item) for item in users]


@router.get("/api/v1/users/visible", response_model=list[UserView])
async def list_visible_users(request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        statement = select(User).order_by(User.username)
        if actor.role == "instructor":
            statement = statement.where(User.role != "admin")
        users = (await session.scalars(statement)).all()
        return [UserView.model_validate(item) for item in users]


@router.post("/api/v1/users", response_model=UserView, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        if await session.scalar(select(User).where(User.username == payload.username)):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre")
        if payload.email and await session.scalar(select(User).where(User.email == payload.email)):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

        created_in_guac = False
        if payload.sync_guacamole:
            try:
                existing = {item.username for item in await request.app.state.guacamole_admin.list_users()}
                if payload.username in existing:
                    raise HTTPException(status_code=409, detail="El usuario ya existe en Guacamole")
                await request.app.state.guacamole_admin.create_user(
                    payload.username,
                    payload.password,
                    email=payload.email,
                    full_name=payload.full_name,
                )
                created_in_guac = True
            except HTTPException:
                raise
            except GuacamoleApiError as exc:
                raise HTTPException(status_code=502, detail=f"No se pudo crear la cuenta en Guacamole: {exc}") from exc

        target = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            full_name=payload.full_name,
            organization=payload.organization,
            user_function=payload.user_function,
            is_active=True,
        )
        session.add(target)
        try:
            await session.flush()
            await write_audit(session, actor.id, "user.create", "user", str(target.id), {"role": payload.role, "guacamole": payload.sync_guacamole})
            await session.commit()
        except Exception:
            await session.rollback()
            if created_in_guac:
                try:
                    await request.app.state.guacamole_admin.delete_user(payload.username)
                except Exception:
                    pass
            raise
        await session.refresh(target)
        return UserView.model_validate(target)


@router.patch("/api/v1/users/{user_id}", response_model=UserView)
async def update_user(user_id: int, payload: UserUpdate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if target.id == actor.id and payload.is_active is False:
            raise HTTPException(status_code=409, detail="No puedes deshabilitar tu propia cuenta")
        values = payload.model_dump(exclude_none=True)
        if target.role in {"admin", "instructor"} and "role" in values and values["role"] != target.role:
            raise HTTPException(status_code=403, detail="Las cuentas de administrador e instructor están protegidas contra cambio de rol")
        if target.id == actor.id and "role" in values and values["role"] != target.role:
            raise HTTPException(status_code=403, detail="No puedes cambiar tu propio rol desde este panel")
        for field, value in values.items():
            setattr(target, field, value)
        if {"is_active", "full_name", "organization"}.intersection(values):
            try:
                await request.app.state.guacamole_admin.update_user(target.username, full_name=target.full_name, disabled=not target.is_active)
            except GuacamoleApiError as exc:
                if exc.status_code != 404:
                    raise HTTPException(status_code=502, detail=f"No se pudo sincronizar el acceso de Guacamole: {exc.detail or exc}") from exc
        await write_audit(session, actor.id, "user.update", "user", str(target.id), values)
        await session.commit()
        await session.refresh(target)
        return UserView.model_validate(target)


@router.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if target.id == actor.id:
            raise HTTPException(status_code=403, detail="No puedes eliminar tu propia cuenta")
        if target.role == "admin":
            admin_count = await session.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True)))
            if int(admin_count or 0) <= 1:
                raise HTTPException(status_code=409, detail="Debe existir al menos un administrador activo")
        try:
            remotes = await request.app.state.guacamole_admin.list_users()
            if any(item.username == target.username for item in remotes):
                await request.app.state.guacamole_admin.delete_user(target.username)
        except GuacamoleApiError as exc:
            if exc.status_code != 404:
                raise HTTPException(status_code=502, detail=f"No se pudo eliminar la cuenta de Guacamole: {exc.detail or exc}") from exc
        await write_audit(session, actor.id, "user.delete", "user", str(target.id), {"username": target.username, "role": target.role, "guacamole": True})
        await session.delete(target)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


