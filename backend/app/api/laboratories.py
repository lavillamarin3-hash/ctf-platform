"""Laboratorios, máquinas virtuales e inventario de infraestructura."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from ..core import get_settings, require_roles
from ..models import Challenge, ChallengeFlag, ChallengeGroupAssignment, GroupMembership, Laboratory, StudentGroup, VMAsset
from ..schemas import LaboratoryCreate, LaboratoryView, VMCreate, VMView
from ..services.bootstrap import laboratory_view, vm_view, write_audit
from ..domain.challenges.catalog import DEMO_VM_IPS
from ..services.challenge_runtime import _asset_ref_key
from ..services.runtime_flags import is_effectively_dynamic
from ..guacamole import GuacamoleApiError


from fastapi import APIRouter

router = APIRouter()

@router.get("/api/v1/laboratories", response_model=list[LaboratoryView])
async def list_laboratories(request: Request, _=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        labs = (await session.scalars(select(Laboratory).options(selectinload(Laboratory.vms)).order_by(Laboratory.id))).unique().all()
        return [laboratory_view(item) for item in labs]

@router.get("/api/v1/player/laboratories", response_model=list[LaboratoryView])
async def list_player_laboratories(request: Request, user=Depends(require_roles("player"))):
    async with request.app.state.session_factory() as session:
        assigned_challenge_ids = select(ChallengeGroupAssignment.challenge_id).join(
            GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id
        ).join(
            StudentGroup, StudentGroup.id == GroupMembership.group_id
        ).where(
            GroupMembership.user_id == user.id,
            StudentGroup.is_active.is_(True),
        )
        challenges = (await session.scalars(
            select(Challenge).where(Challenge.is_published.is_(True), Challenge.id.in_(assigned_challenge_ids))
        )).all()
        refs = {ref for challenge in challenges for ref in (challenge.asset_references or [])}
        if not refs:
            return []
        labs = (await session.scalars(
            select(Laboratory).options(selectinload(Laboratory.vms)).where(
                Laboratory.status.in_(("ready", "planned")),
            ).order_by(Laboratory.id)
        )).unique().all()
        response: list[LaboratoryView] = []
        normalized_refs = {_asset_ref_key(ref) for ref in refs}
        for lab in labs:
            lab_keys = {_asset_ref_key(lab.name), _asset_ref_key(lab.code or "")}
            matching_lab = bool(normalized_refs.intersection(lab_keys))
            vm_views: list[VMView] = []
            for vm in lab.vms:
                if not matching_lab and _asset_ref_key(vm.name) not in normalized_refs:
                    continue
                guac_url = None
                guac_protocol = None
                if vm.guacamole_connection_id:
                    try:
                        connections = await request.app.state.guacamole_admin.list_connections()
                        conn = next((item for item in connections if item.identifier == vm.guacamole_connection_id), None)
                        if conn:
                            guac_protocol = conn.protocol
                            guac_url = await request.app.state.guacamole.direct_connection_url(conn.identifier)
                    except Exception:
                        guac_url = None
                vm_views.append(vm_view(vm, guacamole_url=guac_url, guacamole_protocol=guac_protocol))
            if vm_views:
                response.append(LaboratoryView(id=lab.id, code=lab.code, name=lab.name, description=lab.description, segment=lab.segment, status=lab.status, vms=vm_views))
        return response

@router.post("/api/v1/laboratories", response_model=LaboratoryView, status_code=status.HTTP_201_CREATED)
async def create_laboratory(payload: LaboratoryCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        if await session.scalar(select(Laboratory).where(Laboratory.name == payload.name)):
            raise HTTPException(status_code=409, detail="Ya existe un laboratorio con ese nombre")
        if payload.code and await session.scalar(select(Laboratory).where(Laboratory.code == payload.code)):
            raise HTTPException(status_code=409, detail="Ya existe un laboratorio con ese código")
        item = Laboratory(**payload.model_dump())
        session.add(item)
        await session.flush()
        await write_audit(session, actor.id, "laboratory.create", "laboratory", str(item.id), payload.model_dump())
        await session.commit()
        await session.refresh(item, attribute_names=["vms"])
        return laboratory_view(item)

@router.patch("/api/v1/laboratories/{laboratory_id}", response_model=LaboratoryView)
async def update_laboratory(laboratory_id: int, payload: LaboratoryCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(Laboratory, laboratory_id, options=[selectinload(Laboratory.vms)])
        if item is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        item.code = payload.code
        item.name = payload.name
        item.description = payload.description
        item.segment = payload.segment
        item.status = payload.status
        await write_audit(session, actor.id, "laboratory.update", "laboratory", str(item.id), payload.model_dump())
        await session.commit()
        await session.refresh(item, attribute_names=["vms"])
        return laboratory_view(item)

@router.delete("/api/v1/laboratories/{laboratory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_laboratory(laboratory_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(Laboratory, laboratory_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        await write_audit(session, actor.id, "laboratory.delete", "laboratory", str(item.id), {"name": item.name})
        await session.delete(item)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/api/v1/vms", response_model=VMView, status_code=status.HTTP_201_CREATED)
async def create_vm(payload: VMCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        lab = await session.get(Laboratory, payload.laboratory_id)
        if lab is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        if payload.ip_address:
            allowed = DEMO_VM_IPS.get(payload.network_role, set())
            if payload.ip_address not in allowed:
                raise HTTPException(status_code=422, detail="La IP seleccionada no pertenece al catálogo actual del laboratorio")
            used = await session.scalar(select(VMAsset).where(VMAsset.ip_address == payload.ip_address))
            if used:
                raise HTTPException(status_code=409, detail="La dirección IP ya está asignada")
        item = VMAsset(**payload.model_dump())
        session.add(item)
        await session.flush()
        await write_audit(session, actor.id, "vm.create", "vm", str(item.id), payload.model_dump())
        await session.commit()
        return vm_view(item)

@router.patch("/api/v1/vms/{vm_id}", response_model=VMView)
async def update_vm(vm_id: int, payload: VMCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(VMAsset, vm_id)
        if item is None:
            raise HTTPException(status_code=404, detail="VM no encontrada")
        lab = await session.get(Laboratory, payload.laboratory_id)
        if lab is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        if payload.ip_address:
            allowed = DEMO_VM_IPS.get(payload.network_role, set())
            if payload.ip_address not in allowed:
                raise HTTPException(status_code=422, detail="La IP seleccionada no pertenece al catálogo actual del laboratorio")
            used = await session.scalar(select(VMAsset).where(VMAsset.ip_address == payload.ip_address, VMAsset.id != vm_id))
            if used:
                raise HTTPException(status_code=409, detail="La dirección IP ya está asignada")
        for field, value in payload.model_dump().items():
            if field != "laboratory_id":
                setattr(item, field, value)
        item.laboratory_id = payload.laboratory_id
        await write_audit(session, actor.id, "vm.update", "vm", str(item.id), payload.model_dump())
        await session.commit()
        await session.refresh(item)
        return vm_view(item)

@router.delete("/api/v1/vms/{vm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vm(vm_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(VMAsset, vm_id)
        if item is None:
            raise HTTPException(status_code=404, detail="VM no encontrada")
        await write_audit(session, actor.id, "vm.delete", "vm", str(item.id), {"name": item.name})
        await session.delete(item)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/admin/lab-ssh/verify")
async def verify_ssh_lab(request: Request, _=Depends(require_roles("admin"))):
    """Diagnóstico de solo lectura para el laboratorio SSH real.

    No crea ni modifica laboratorios, VMs, retos, flags ni asignaciones.
    """
    target_ip = "192.168.146.137"
    vm_name = "LAB-LNXVICT"
    challenge_code = "LAB-01"
    settings = get_settings()

    try:
        connections = await request.app.state.guacamole_admin.list_connections()
        guac_error = None
    except GuacamoleApiError as exc:
        connections = []
        guac_error = exc.detail or str(exc)

    ssh_connection = next(
        (connection for connection in connections if connection.protocol == "ssh" and (connection.hostname or "").strip() == target_ip),
        None,
    )

    async with request.app.state.session_factory() as session:
        vm = await session.scalar(select(VMAsset).where(VMAsset.name == vm_name))
        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == challenge_code))
        dynamic_flags = [
            flag for flag in (challenge.flags if challenge else [])
            if is_effectively_dynamic(challenge_code, flag)
        ]

    return {
        "read_only": True,
        "victim": {"name": vm_name, "ip": target_ip},
        "guacamole": {
            "reachable": guac_error is None,
            "ssh_connection_found": ssh_connection is not None,
            "connection_id": ssh_connection.identifier if ssh_connection else None,
            "connection_name": ssh_connection.name if ssh_connection else None,
        },
        "database_state": {
            "vm_found": vm is not None,
            "vm_has_matching_ip": bool(vm and vm.ip_address == target_ip),
            "vm_has_guacamole_id": bool(vm and vm.guacamole_connection_id),
            "challenge_found": challenge is not None,
            "dynamic_flag_count": len(dynamic_flags),
        },
        "injector": {
            "enabled": settings.flag_injector_enabled,
            "remote_script": settings.flag_injector_remote_script,
            "path": settings.flag_injector_flag_path,
            "ssh_port": settings.flag_injector_ssh_port,
        },
        "ready_for_dynamic_lab": all((
            guac_error is None,
            ssh_connection is not None,
            vm is not None,
            vm and vm.ip_address == target_ip,
            vm and vm.guacamole_connection_id,
            challenge is not None,
            len(dynamic_flags) >= 1,
            settings.flag_injector_enabled,
        )),
    }

