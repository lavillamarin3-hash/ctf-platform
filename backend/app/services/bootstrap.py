"""Inicialización de infraestructura, seed y transformadores de respuesta."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, WebSocket, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..core import get_settings, hash_password
from ..db import create_schema, make_session_factory
from ..guacamole import make_guacamole_adapter, make_guacamole_admin
from ..models import (
    AuditEvent, Challenge, ChallengeCompletion, ChallengeFlag, Laboratory,
    Role, User, VMAsset,
)
from ..schemas import ChallengeView, LaboratoryView, VMView

def vm_view(item: VMAsset, *, guacamole_url: str | None = None, guacamole_protocol: str | None = None) -> VMView:
    return VMView(
        id=item.id, laboratory_id=item.laboratory_id, name=item.name, os=item.os, ip_address=item.ip_address,
        vlan=item.vlan, role=item.role, network_role=item.network_role, subnet=item.subnet, profile=item.profile,
        baseline=item.baseline, nutanix_vm_id=item.nutanix_vm_id, guacamole_connection_id=item.guacamole_connection_id,
        guacamole_url=guacamole_url, guacamole_protocol=guacamole_protocol, status=item.status
    )

def laboratory_view(item: Laboratory) -> LaboratoryView:
    return LaboratoryView(
        id=item.id, code=item.code, name=item.name, description=item.description, segment=item.segment, status=item.status,
        vms=[vm_view(vm) for vm in item.vms]
    )

class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        for websocket in list(self.connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket)


async def write_audit(session, actor_id: int | None, action: str, entity_type: str, entity_id: str, details: dict | None = None) -> None:
    session.add(AuditEvent(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))


async def seed_data(session_factory) -> None:
    settings = get_settings()
    async with session_factory() as session:
        roles = {
            "admin": "Administración completa de la plataforma",
            "instructor": "Diseño y seguimiento de retos",
            "player": "Participante de retos",
            "guest": "Consulta de solo lectura",
        }
        for name, description in roles.items():
            if not await session.scalar(select(Role).where(Role.name == name)):
                session.add(Role(name=name, description=description))

        # Desde esta fase no se crean cuentas ficticias automáticamente.
        # Los usuarios reales se crean desde Administración > Gestionar usuarios y,
        # por defecto, se sincronizan con Guacamole.

        await session.flush()

        # El inventario/retos de demostración solo se conserva para instalaciones
        # que ya lo tengan; no se presentan como usuarios ficticios en la interfaz.
        if not settings.ctf_seed_demo_data:
            await session.commit()
            return

        inventory = [
            {"code": "LAB-ATACANTES", "name": "Laboratorio de Atacantes", "segment": "VLAN 20 · 10.10.20.0/24", "vms": [
                ("LAB-KALI", "Kali Linux 2026.2", "10.10.20.10", "Atacantes", "VLAN 20", "10.10.20.0/24", "standard"),
                ("LAB-KALI-PURPLE", "Kali Linux Purple 2026.2", "10.10.20.11", "Atacantes", "VLAN 20", "10.10.20.0/24", "standard"),
                ("LAB-KALI-BLUE", "Linux Mint", "10.10.20.12", "Atacantes", "VLAN 20", "10.10.20.0/24", "standard"),
            ]},
            {"code": "LAB-VICTIMAS", "name": "Laboratorio de Víctimas", "segment": "VLAN 30 · 10.10.30.0/24", "vms": [
                ("LAB-WINVICT-A", "Windows 10 (ES)", "10.10.30.10", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-WINVICT-B", "Windows 10 (ES)", "10.10.30.11", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-LNXVICT", "Ubuntu Server 26.04", "192.168.146.137", "Víctimas", "RED ACTUAL", "192.168.146.0/24", "vulnerable"),
                ("LAB-SRVWEB", "Ubuntu Server 26.04", "10.10.30.20", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-SRVFSAD", "Ubuntu Server 26.04", "10.10.30.21", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
            ]},
        ]
        for lab_data in inventory:
            lab = await session.scalar(select(Laboratory).where(Laboratory.code == lab_data["code"]))
            if lab is None:
                lab = Laboratory(code=lab_data["code"], name=lab_data["name"], description=f"{lab_data['segment']} · Cyber range", segment=lab_data["segment"], status="ready")
                session.add(lab)
                await session.flush()
            for vm_name, os_name, ip, net_role, vlan, subnet, profile in lab_data["vms"]:
                vm = await session.scalar(select(VMAsset).where(VMAsset.name == vm_name))
                if vm is None:
                    session.add(VMAsset(laboratory_id=lab.id, name=vm_name, os=os_name, ip_address=ip, vlan=vlan, role=net_role, network_role=net_role, subnet=subnet, profile=profile, status="ready"))

        await session.flush()
        for item in SEED_CHALLENGES:
            challenge = await session.scalar(select(Challenge).where(Challenge.code == item["code"]))
            if challenge is None:
                flag_values = item.get("flag_values", [])
                challenge_data = {key: value for key, value in item.items() if key not in {"flag_values"}}
                challenge = Challenge(**challenge_data)
                session.add(challenge)
                await session.flush()
                for order, flag_value in enumerate(flag_values, start=1):
                    session.add(ChallengeFlag(challenge_id=challenge.id, label=f"Flag {order}", flag_hash=hash_password(flag_value), flag_order=order, is_active=True))
            else:
                # Completa campos nuevos en instalaciones que ya tenían los retos anteriores.
                changed = False
                for key in ("category", "scenario"):
                    value = item.get(key)
                    if getattr(challenge, key, None) != value and (getattr(challenge, key, None) in (None, "", "MISC")):
                        setattr(challenge, key, value)
                        changed = True
                active_flags = await session.scalars(select(ChallengeFlag).where(ChallengeFlag.challenge_id == challenge.id, ChallengeFlag.is_active.is_(True)))
                if not list(active_flags) and item.get("flag_values"):
                    for order, flag_value in enumerate(item["flag_values"], start=1):
                        session.add(ChallengeFlag(challenge_id=challenge.id, label=f"Flag {order}", flag_hash=hash_password(flag_value), flag_order=order, is_active=True))
                    changed = True
                if changed:
                    session.add(challenge)
        await session.commit()


async def ranking_rows(session_factory) -> list[dict]:
    async with session_factory() as session:
        statement = (
            select(
                User.username,
                func.coalesce(func.sum(ChallengeCompletion.awarded_points), 0).label("total_points"),
                func.count(ChallengeCompletion.id).label("challenges_completed"),
            )
            .outerjoin(ChallengeCompletion, ChallengeCompletion.user_id == User.id)
            .where(User.role == "player", User.is_active.is_(True))
            .group_by(User.id, User.username)
            .order_by(func.coalesce(func.sum(ChallengeCompletion.awarded_points), 0).desc(), func.min(ChallengeCompletion.completed_at).asc().nullslast(), User.username.asc())
        )
        data = (await session.execute(statement)).all()
        return [
            {"position": index, "username": row.username, "total_points": int(row.total_points), "challenges_completed": int(row.challenges_completed)}
            for index, row in enumerate(data, start=1)
        ]


async def check_rate_limit(redis_client, key: str, maximum: int = 8, window_seconds: int = 60) -> None:
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count > maximum:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados intentos. Espera un minuto antes de continuar.")
    except HTTPException:
        raise
    except Exception:
        # Redis mejora la defensa, pero una indisponibilidad no debe convertir la plataforma en una denegación de servicio.
        return


def challenge_view(challenge: Challenge, completed: bool = False, include_flags: bool = False) -> ChallengeView:
    flags = None
    if include_flags:
        flags = [{"id": item.id, "label": item.label, "flag_order": item.flag_order, "is_active": item.is_active, "mode": item.mode, "template": item.template} for item in challenge.flags]
    return ChallengeView(
        id=challenge.id,
        code=challenge.code,
        name=challenge.name,
        description=challenge.description,
        instructions=challenge.instructions,
        difficulty=challenge.difficulty,
        category=challenge.category,
        scenario=challenge.scenario,
        mitre_technique=challenge.mitre_technique,
        asset_references=challenge.asset_references,
        points=challenge.points,
        is_published=challenge.is_published,
        flag_count=len(challenge.flags),
        completed=completed,
        flags=flags,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.session_factory = make_session_factory()
    await create_schema(app.state.session_factory)
    await seed_data(app.state.session_factory)
    app.state.redis = redis.from_url(get_settings().redis_url, decode_responses=True)
    app.state.guacamole = make_guacamole_adapter()
    app.state.guacamole_admin = make_guacamole_admin()
    app.state.sockets = ConnectionManager()
    yield
    await app.state.redis.aclose()
