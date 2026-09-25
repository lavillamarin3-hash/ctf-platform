"""Gestión de grupos académicos y sincronización con Guacamole."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..core import require_roles
from ..guacamole import GuacamoleApiError
from ..models import Challenge, ChallengeGroupAssignment, GroupMembership, StudentGroup, User
from ..schemas import GroupCreate, GroupView, GroupMemberAdd
from ..services.bootstrap import write_audit
from ..services.challenge_runtime import _sync_guacamole_group_permissions, _sync_group_members_guacamole_permissions


from fastapi import APIRouter

router = APIRouter()

@router.get("/api/v1/groups", response_model=list[GroupView])
async def list_groups(request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        groups = (await session.scalars(
            select(StudentGroup)
            .options(
                selectinload(StudentGroup.members).selectinload(GroupMembership.user),
                selectinload(StudentGroup.challenge_assignments).selectinload(ChallengeGroupAssignment.challenge),
            )
            .order_by(StudentGroup.name)
        )).unique().all()
        return [GroupView.from_model(group) for group in groups]


async def _group_view(request: Request, group_id: int) -> GroupView:
    async with request.app.state.session_factory() as session:
        group = await session.get(
            StudentGroup,
            group_id,
            options=[
                selectinload(StudentGroup.members).selectinload(GroupMembership.user),
                selectinload(StudentGroup.challenge_assignments).selectinload(ChallengeGroupAssignment.challenge),
            ],
        )
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        return GroupView.from_model(group)


async def create_group(payload: GroupCreate, request: Request, actor=Depends(require_roles("admin"))):
    guac_identifier = payload.code.strip().upper()
    created_in_guac = False
    try:
        await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=not payload.is_active)
        created_in_guac = True
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502 if exc.status_code not in (400,409) else 409, detail=f"No se pudo crear el grupo en Guacamole: {exc.detail or exc}") from exc

    async with request.app.state.session_factory() as session:
        if await session.scalar(select(StudentGroup).where(StudentGroup.code == payload.code)):
            if created_in_guac:
                try: await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
                except Exception: pass
            raise HTTPException(status_code=409, detail="Ya existe un grupo con ese código")
        if await session.scalar(select(StudentGroup).where(StudentGroup.name == payload.name)):
            if created_in_guac:
                try: await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
                except Exception: pass
            raise HTTPException(status_code=409, detail="Ya existe un grupo con ese nombre")
        group = StudentGroup(name=payload.name, code=payload.code, description=payload.description, is_active=payload.is_active, guacamole_group_identifier=guac_identifier, created_by=actor.id)
        session.add(group)
        try:
            await session.flush()
            await write_audit(session, actor.id, "group.create", "group", str(group.id), {**payload.model_dump(), "guacamole_group": guac_identifier})
            await session.commit()
        except Exception:
            await session.rollback()
            if created_in_guac:
                try: await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
                except Exception: pass
            raise
    return await _group_view(request, group.id)


@router.patch("/api/v1/groups/{group_id}", response_model=GroupView)
async def update_group(group_id: int, payload: GroupCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        duplicate_code = await session.scalar(select(StudentGroup).where(StudentGroup.code == payload.code, StudentGroup.id != group_id))
        duplicate_name = await session.scalar(select(StudentGroup).where(StudentGroup.name == payload.name, StudentGroup.id != group_id))
        if duplicate_code or duplicate_name:
            raise HTTPException(status_code=409, detail="Ya existe otro grupo con ese código o nombre")
        group.name = payload.name
        group.code = payload.code
        group.description = payload.description
        group.is_active = payload.is_active
        guac_identifier = group.guacamole_group_identifier or payload.code
        group.guacamole_group_identifier = guac_identifier
        await write_audit(session, actor.id, "group.update", "group", str(group.id), {**payload.model_dump(), "guacamole_group": guac_identifier})
        await session.commit()
    try:
        if guac_identifier:
            try:
                await request.app.state.guacamole_admin.update_user_group(guac_identifier, disabled=not payload.is_active)
            except GuacamoleApiError as exc:
                if exc.status_code == 404:
                    await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=not payload.is_active)
                else:
                    raise
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo sincronizar el grupo con Guacamole: {exc.detail or exc}") from exc
    return await _group_view(request, group_id)


@router.delete("/api/v1/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id, options=[selectinload(StudentGroup.members)])
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        member_ids = [member.user_id for member in group.members]
        guac_identifier = group.guacamole_group_identifier or group.code
        await write_audit(session, actor.id, "group.delete", "group", str(group.id), {"name": group.name, "code": group.code, "member_count": len(member_ids), "guacamole_group": guac_identifier})
        await session.delete(group)
        await session.commit()
    if guac_identifier:
        try:
            await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code != 404:
                raise HTTPException(status_code=502, detail=f"No se pudo eliminar el grupo de Guacamole: {exc.detail or exc}") from exc
    for user_id in member_ids:
        await _sync_player_guacamole_permissions(request, int(user_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/v1/groups/{group_id}/members", response_model=GroupView)
async def add_group_member(group_id: int, payload: GroupMemberAdd, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        target = await session.get(User, payload.user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        if target is None or target.role != "player" or not target.is_active:
            raise HTTPException(status_code=422, detail="Solo se pueden agregar estudiantes activos")
        exists = await session.scalar(select(GroupMembership).where(GroupMembership.group_id == group_id, GroupMembership.user_id == payload.user_id))
        if not exists:
            session.add(GroupMembership(group_id=group_id, user_id=payload.user_id))
            await write_audit(session, actor.id, "group.member.add", "group", str(group_id), {"user_id": payload.user_id})
            await session.commit()
    async with request.app.state.session_factory() as session:
        row = await session.get(StudentGroup, group_id)
        target = await session.get(User, payload.user_id)
        guac_identifier = row.guacamole_group_identifier if row else None
        username = target.username if target else None
        if row is not None and not guac_identifier:
            guac_identifier = row.code
            row.guacamole_group_identifier = guac_identifier
            await session.commit()
    if guac_identifier and username:
        try:
            await request.app.state.guacamole_admin.get_user_group_permissions(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code == 404:
                try: await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=False)
                except GuacamoleApiError as create_exc:
                    raise HTTPException(status_code=502, detail=f"No se pudo crear el grupo en Guacamole: {create_exc.detail or create_exc}") from create_exc
            else:
                raise HTTPException(status_code=502, detail=f"No se pudo verificar el grupo en Guacamole: {exc.detail or exc}") from exc
        try: await request.app.state.guacamole_admin.add_user_group_member(guac_identifier, username)
        except GuacamoleApiError as exc:
            raise HTTPException(status_code=502, detail=f"No se pudo añadir el estudiante al grupo de Guacamole: {exc.detail or exc}") from exc
    await _sync_player_guacamole_permissions(request, payload.user_id)
    return await _group_view(request, group_id)


@router.delete("/api/v1/groups/{group_id}/members/{user_id}", response_model=GroupView)
async def remove_group_member(group_id: int, user_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        membership = await session.scalar(select(GroupMembership).where(GroupMembership.group_id == group_id, GroupMembership.user_id == user_id))
        if membership:
            await session.delete(membership)
            await write_audit(session, actor.id, "group.member.remove", "group", str(group_id), {"user_id": user_id})
            await session.commit()
    async with request.app.state.session_factory() as session:
        row = await session.get(StudentGroup, group_id)
        target = await session.get(User, user_id)
        guac_identifier = row.guacamole_group_identifier if row else None
        username = target.username if target else None
    if guac_identifier and username:
        try: await request.app.state.guacamole_admin.remove_user_group_member(guac_identifier, username)
        except GuacamoleApiError as exc:
            if exc.status_code != 404:
                raise HTTPException(status_code=502, detail=f"No se pudo retirar el estudiante del grupo de Guacamole: {exc.detail or exc}") from exc
    await _sync_player_guacamole_permissions(request, user_id)
    return await _group_view(request, group_id)


@router.put("/api/v1/challenges/{code}/groups/{group_id}", response_model=GroupView)
async def assign_challenge_group(code: str, group_id: int, request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
        group = await session.get(StudentGroup, group_id)
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        exists = await session.scalar(select(ChallengeGroupAssignment).where(ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group_id))
        if not exists:
            session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group_id, created_by=actor.id))
            await write_audit(session, actor.id, "challenge.group.assign", "challenge", str(challenge.id), {"group_id": group_id, "code": code})
            await session.commit()
    await _sync_guacamole_group_permissions(request, group_id)
    return await _group_view(request, group_id)


@router.delete("/api/v1/challenges/{code}/groups/{group_id}", response_model=GroupView)
async def unassign_challenge_group(code: str, group_id: int, request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        assignment = await session.scalar(select(ChallengeGroupAssignment).where(ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group_id))
        if assignment:
            await session.delete(assignment)
            await write_audit(session, actor.id, "challenge.group.unassign", "challenge", str(challenge.id), {"group_id": group_id, "code": code})
            await session.commit()
    await _sync_guacamole_group_permissions(request, group_id)
    return await _group_view(request, group_id)


