"""Servicios de ejecución: flags dinámicas, sincronización Guacamole y selección de VM."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..guacamole import GuacamoleApiError
from ..models import Challenge, ChallengeGroupAssignment, GroupMembership, Laboratory, StudentGroup, User, VMAsset

def render_dynamic_flag(template: str, *, code: str, username: str, run_id: int) -> str:
    # Cleartext is generated only for the current run. Only its hash is persisted.
    value = template
    value = value.replace("{{CODE}}", code)
    value = value.replace("{{USER}}", username)
    value = value.replace("{{RUN_ID}}", str(run_id))
    value = value.replace("{{RAND}}", secrets.token_hex(8))
    return value


# ============================================================
# EJECUCIÓN Y VALIDACIÓN DE RETOS
# ============================================================

def _asset_ref_key(value: str) -> str:
    return value.strip().upper()


async def _sync_player_guacamole_permissions(request: Request, user_id: int) -> None:
    """Concede a un jugador solo las conexiones Guacamole de los retos de sus grupos."""
    async with request.app.state.session_factory() as session:
        user = await session.get(User, user_id)
        if user is None or user.role != "player":
            return

        assigned_challenges = (
            await session.scalars(
                select(Challenge)
                .join(ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == Challenge.id)
                .join(GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id)
                .join(StudentGroup, StudentGroup.id == GroupMembership.group_id)
                .where(GroupMembership.user_id == user_id, StudentGroup.is_active.is_(True))
            )
        ).unique().all()

        vms = (await session.scalars(select(VMAsset))).all()
        refs_to_connections: dict[str, str] = {}
        for vm in vms:
            if vm.guacamole_connection_id:
                refs_to_connections[_asset_ref_key(vm.name)] = vm.guacamole_connection_id
                if vm.ip_address:
                    refs_to_connections[_asset_ref_key(vm.ip_address)] = vm.guacamole_connection_id

        lab_rows = (await session.scalars(select(Laboratory))).all()
        labs_by_key: dict[str, int] = {}
        for lab in lab_rows:
            labs_by_key[_asset_ref_key(lab.name)] = lab.id
            if lab.code:
                labs_by_key[_asset_ref_key(lab.code)] = lab.id

        lab_vms = (await session.scalars(select(VMAsset))).all()
        vm_by_lab: dict[int, list[VMAsset]] = {}
        for vm in lab_vms:
            vm_by_lab.setdefault(vm.laboratory_id, []).append(vm)

        desired: dict[str, list[str]] = {}
        for challenge in assigned_challenges:
            for raw_ref in challenge.asset_references or []:
                key = _asset_ref_key(raw_ref)
                direct = refs_to_connections.get(key)
                if direct:
                    desired[direct] = ["READ"]
                    continue
                lab_id = labs_by_key.get(key)
                if lab_id:
                    for vm in vm_by_lab.get(lab_id, []):
                        if vm.guacamole_connection_id:
                            desired[vm.guacamole_connection_id] = ["READ"]

    try:
        await request.app.state.guacamole_admin.patch_user_permissions(
            user.username,
            system_permissions=[],
            connection_permissions=desired,
        )
    except GuacamoleApiError as exc:
        if exc.status_code != 404:
            raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar los permisos de Guacamole: {exc.detail or exc}") from exc


async def _sync_guacamole_group_permissions(request: Request, group_id: int) -> None:
    """Sincroniza un grupo académico con un user group real de Guacamole. Los permisos READ se heredan a sus miembros."""
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        if group is None:
            return
        if not group.guacamole_group_identifier:
            group.guacamole_group_identifier = group.code
            await session.commit()
        assigned_challenges = (await session.scalars(
            select(Challenge)
            .join(ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == Challenge.id)
            .where(ChallengeGroupAssignment.group_id == group_id)
        )).unique().all()
        vms = (await session.scalars(select(VMAsset))).all()
        refs_to_connections: dict[str, str] = {}
        for vm in vms:
            if vm.guacamole_connection_id:
                refs_to_connections[_asset_ref_key(vm.name)] = vm.guacamole_connection_id
                if vm.ip_address:
                    refs_to_connections[_asset_ref_key(vm.ip_address)] = vm.guacamole_connection_id
        labs = (await session.scalars(select(Laboratory))).all()
        labs_by_key = {_asset_ref_key(l.code or ""): l.id for l in labs if l.code}
        labs_by_key.update({_asset_ref_key(l.name): l.id for l in labs})
        vm_by_lab: dict[int, list[VMAsset]] = {}
        for vm in vms: vm_by_lab.setdefault(vm.laboratory_id, []).append(vm)
        desired: dict[str, list[str]] = {}
        for challenge in assigned_challenges:
            for raw_ref in challenge.asset_references or []:
                key = _asset_ref_key(raw_ref)
                direct = refs_to_connections.get(key)
                if direct: desired[direct] = ["READ"]; continue
                lab_id = labs_by_key.get(key)
                if lab_id:
                    for vm in vm_by_lab.get(lab_id, []):
                        if vm.guacamole_connection_id: desired[vm.guacamole_connection_id] = ["READ"]
        guac_identifier = group.guacamole_group_identifier
    try:
        try:
            await request.app.state.guacamole_admin.get_user_group_permissions(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code == 404:
                await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=False)
            else: raise
        await request.app.state.guacamole_admin.patch_user_group_permissions(guac_identifier, connection_permissions=desired)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar permisos del grupo con Guacamole: {exc.detail or exc}") from exc


async def _sync_group_members_guacamole_permissions(request: Request, group_id: int) -> None:
    async with request.app.state.session_factory() as session:
        user_ids = list((await session.scalars(select(GroupMembership.user_id).where(GroupMembership.group_id == group_id))).all())
    for user_id in user_ids:
        await _sync_player_guacamole_permissions(request, int(user_id))


async def _find_challenge_vm(session, challenge: Challenge):
    """Busca una VM lista y asociada al reto mediante asset_references."""
    refs = {_asset_ref_key(value) for value in (challenge.asset_references or []) if value.strip()}
    if not refs:
        return None, None

    labs = (
        await session.scalars(
            select(Laboratory)
            .options(selectinload(Laboratory.vms))
            .where(Laboratory.status.in_(("ready", "planned")))
            .order_by(Laboratory.id)
        )
    ).unique().all()

    for lab in labs:
        lab_keys = {_asset_ref_key(lab.code or ""), _asset_ref_key(lab.name)}
        for vm in lab.vms:
            vm_keys = {_asset_ref_key(vm.name)} | lab_keys
            if refs.intersection(vm_keys) and vm.status == "ready" and vm.guacamole_connection_id:
                return lab, vm
    return None, None
