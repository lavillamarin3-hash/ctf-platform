"""Laboratorios, máquinas virtuales e inventario de infraestructura."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from ..core import require_roles
from ..models import Laboratory, RemoteAccessAssignment, VMAsset
from ..schemas import LaboratoryCreate, LaboratoryView, VMCreate, VMView
from ..services.bootstrap import DEMO_VM_IPS, laboratory_view, vm_view, write_audit


from fastapi import APIRouter

router = APIRouter()

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


@router.post("/api/v1/admin/lab-ssh/prepare")
async def prepare_ssh_demo_lab(request: Request, actor=Depends(require_roles("admin"))):
    """Prepara el laboratorio real SSH de demostración usando la VM/IP actuales y una conexión SSH existente en Guacamole."""
    target_ip = "192.168.146.137"
    attacker_ip = "192.168.146.134"
    lab_code = "LAB-SSH-01"
    vm_name = "LAB-LNXVICT"
    challenge_code = "LAB-01"
    static_flag = "FLAG{ssh_lab_demo}"

    try:
        connections = await request.app.state.guacamole_admin.list_connections()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar Guacamole: {exc.detail or exc}") from exc

    connection = next((c for c in connections if c.protocol == "ssh" and (c.hostname or "").strip() == target_ip), None)
    if connection is None:
        raise HTTPException(status_code=409, detail=f"No existe una conexión SSH de Guacamole asociada a {target_ip}. Créala primero en Administración > Guacamole.")

    async with request.app.state.session_factory() as session:
        lab = await session.scalar(select(Laboratory).options(selectinload(Laboratory.vms)).where(Laboratory.code == lab_code))
        if lab is None:
            lab = Laboratory(code=lab_code, name="Laboratorio SSH · Demostración", description="Laboratorio real de reconocimiento controlado sobre la VM LAB-LNXVICT.", segment="Red actual · Víctima 192.168.146.137", status="ready")
            session.add(lab)
            await session.flush()
        else:
            lab.status = "ready"

        vm = await session.scalar(select(VMAsset).where(VMAsset.name == vm_name))
        if vm is None:
            vm = VMAsset(laboratory_id=lab.id, name=vm_name, os="Linux / VM de laboratorio", ip_address=target_ip, vlan="RED ACTUAL", role="Víctima", network_role="Víctimas", subnet="192.168.146.0/24", profile="vulnerable", status="ready", guacamole_connection_id=connection.identifier)
            session.add(vm)
        else:
            vm.laboratory_id = lab.id
            vm.ip_address = target_ip
            vm.network_role = "Víctimas"
            vm.role = "Víctima"
            vm.guacamole_connection_id = connection.identifier
            vm.status = "ready"

        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == challenge_code))
        challenge_payload = {
            "name": "Reconocimiento SSH controlado",
            "description": "Identifica el servicio SSH de la máquina víctima del laboratorio y localiza la evidencia del ejercicio.",
            "instructions": "Trabaja únicamente dentro del laboratorio autorizado. Desde la Kali atacante identifica el servicio SSH en 192.168.146.137, conéctate con las credenciales proporcionadas por el instructor y localiza /opt/ctf/flag.txt. No realices acciones fuera del entorno.",
            "difficulty": "Básico",
            "category": "MISC",
            "scenario": "LAB-SSH-REAL",
            "mitre_technique": "T1046 — Network Service Scanning",
            "asset_references": [vm_name, lab_code, target_ip],
            "points": 100,
            "is_published": True,
        }
        if challenge is None:
            challenge = Challenge(**challenge_payload, created_by=actor.id)
            session.add(challenge)
            await session.flush()
        else:
            for key, value in challenge_payload.items():
                setattr(challenge, key, value)

        active_static = next((f for f in challenge.flags if f.is_active and f.mode == "static"), None)
        if active_static is None:
            session.add(ChallengeFlag(challenge_id=challenge.id, label="Flag SSH", flag_hash=hash_password(static_flag), flag_order=1, is_active=True, mode="static"))
        else:
            active_static.flag_hash = hash_password(static_flag)
            active_static.mode = "static"
            active_static.template = None
            active_static.label = "Flag SSH"
            active_static.flag_order = 1
        await write_audit(session, actor.id, "lab.demo.prepare", "laboratory", str(lab.id), {"lab_code": lab_code, "vm": vm_name, "ip": target_ip, "attacker_ip": attacker_ip, "guacamole_connection": connection.identifier, "challenge": challenge_code})
        await session.commit()

    return {
        "laboratory": {"id": lab.id, "code": lab.code, "name": lab.name},
        "vm": {"id": vm.id, "name": vm.name, "ip": vm.ip_address, "protocol": connection.protocol, "guacamole_connection_id": connection.identifier, "guacamole_connection_name": connection.name},
        "challenge": {"code": challenge.code, "name": challenge.name, "points": challenge.points, "flag_mode": "static"},
        "attacker_ip": attacker_ip,
        "victim_ip": target_ip,
        "flag": "FLAG{ssh_lab_demo}",
        "note": "La flag estática se valida por hash. La VM ya debe contener /opt/ctf/flag.txt con el mismo valor.",
    }


