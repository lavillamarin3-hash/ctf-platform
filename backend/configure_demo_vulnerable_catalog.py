"""Crea retos estáticos para el paquete demo-vulnerable, de forma opt-in.

Ejecutar en una TTY del contenedor API. Las banderas se solicitan sin eco y no
se imprimen ni se guardan en archivos del repositorio.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.challenges import require_idle_challenge
from app.core import hash_password
from app.db import make_session_factory
from app.models import (
    Challenge,
    ChallengeFlag,
    ChallengeGroupAssignment,
    Laboratory,
    StudentGroup,
    VMAsset,
)

FLAG_PATTERN = re.compile(r"^FLAG\{[^\r\n}]{8,120}\}$")
SPECS = (
    {
        "code": "DEMO-SSH-CONTAINER",
        "name": "Demo SSH: credenciales débiles controladas",
        "category": "REDES",
        "scenario": "DEMO-SSH-CONTAINER",
        "mitre": "T1110.001 — Password Guessing",
        "assets": ["LAB-KALI-BLUE", "LAB-LNXVICT"],
        "points": 100,
        "flag_key": "ssh",
        "instructions": (
            "Abre LAB-KALI-BLUE mediante Guacamole. Investiga únicamente "
            "10.10.30.12:22222, usa el usuario y diccionario autorizados por "
            "el instructor, y recupera la evidencia con el shell restringido. "
            "No pruebes SSH administrativo en 22 ni otros destinos."
        ),
    },
    {
        "code": "DEMO-WEB-SQLI",
        "name": "Demo web: portal SQL vulnerable controlado",
        "category": "WEB",
        "scenario": "DEMO-WEB-SQLI",
        "mitre": "T1190 — Exploit Public-Facing Application",
        "assets": ["LAB-KALI-PURPLE", "LAB-SRVWEB"],
        "points": 100,
        "flag_key": "web",
        "instructions": (
            "Abre LAB-KALI-PURPLE mediante Guacamole y accede únicamente a "
            "http://10.10.30.20:8088/. Analiza el inicio de sesión del portal "
            "de práctica y recupera la evidencia asignada. No escanees otros "
            "puertos, rutas, hosts ni servicios."
        ),
    },
)
EXPECTED_VMS = {
    "LAB-LNXVICT": ("10.10.30.12", ("linux", "ubuntu")),
    "LAB-SRVWEB": ("10.10.30.20", ("linux", "ubuntu")),
    "LAB-KALI-BLUE": ("10.10.20.12", ("kali",)),
    "LAB-KALI-PURPLE": ("10.10.20.11", ("kali",)),
}


async def ready_assets(session) -> None:
    labs = (await session.scalars(select(Laboratory))).all()
    rows = (await session.scalars(select(VMAsset))).all()
    for name, (ip, os_tokens) in EXPECTED_VMS.items():
        matches = [item for item in rows if item.name == name and item.ip_address == ip]
        if len(matches) != 1:
            raise ValueError(f"{name} debe existir una única vez con IP {ip}.")
        vm = matches[0]
        lab = next((item for item in labs if item.id == vm.laboratory_id), None)
        if vm.status != "ready" or lab is None or lab.status != "ready":
            raise ValueError(f"{name} y su laboratorio deben estar en estado ready.")
        if not any(token in vm.os.lower() for token in os_tokens):
            raise ValueError(f"{name} tiene un sistema operativo no compatible en el inventario.")


def validate_flag(label: str, value: str) -> str:
    if not FLAG_PATTERN.fullmatch(value):
        raise ValueError(f"La bandera {label} debe tener formato FLAG{{...}} y no contener saltos de línea.")
    return value


async def configure(session, group_code: str, flags: dict[str, str] | None, *, apply: bool) -> dict:
    group = await session.scalar(
        select(StudentGroup).where(StudentGroup.code == group_code, StudentGroup.is_active.is_(True))
    )
    if group is None:
        raise ValueError("El grupo indicado no existe o está inactivo.")
    await ready_assets(session)
    changes: list[str] = []

    for spec in SPECS:
        challenge = await session.scalar(
            select(Challenge).options(selectinload(Challenge.flags))
            .where(Challenge.code == spec["code"]).with_for_update()
        )
        if challenge is None:
            changes.append(f"Crear {spec['code']} en borrador con bandera estática.")
            changes.append(f"Asignar {spec['code']} a {group_code}.")
            if apply:
                challenge = Challenge(
                    code=spec["code"],
                    name=spec["name"],
                    description="Reto aislado para la demostración técnica del laboratorio CoCiber.",
                    instructions=spec["instructions"],
                    difficulty="Básico",
                    category=spec["category"],
                    scenario=spec["scenario"],
                    mitre_technique=spec["mitre"],
                    asset_references=spec["assets"],
                    points=spec["points"],
                    is_published=False,
                )
                challenge.flags = [
                    ChallengeFlag(
                        label=f"Bandera estática {spec['code']}",
                        mode="static",
                        flag_hash=hash_password(flags[spec["flag_key"]]),
                        template=None,
                        flag_order=1,
                        is_active=True,
                    )
                ]
                session.add(challenge)
                await session.flush()
                session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))
        else:
            await require_idle_challenge(session, challenge.id)
            active = [flag for flag in challenge.flags if flag.is_active]
            if (
                challenge.scenario != spec["scenario"]
                or challenge.asset_references != spec["assets"]
                or len(active) != 1
                or active[0].mode != "static"
                or not active[0].flag_hash
            ):
                raise ValueError(f"{spec['code']} existe con una configuración incompatible; revísalo manualmente.")

        if challenge is not None:
            assigned = await session.scalar(
                select(ChallengeGroupAssignment.id).where(
                    ChallengeGroupAssignment.challenge_id == challenge.id,
                    ChallengeGroupAssignment.group_id == group.id,
                )
            )
            if assigned is None:
                changes.append(f"Asignar {spec['code']} a {group_code}.")
                if apply:
                    session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group.id))

    return {"applied": apply, "group": group_code, "changes": changes, "published": False}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", required=True, help="Código de grupo activo")
    parser.add_argument("--apply", action="store_true", help="Crea los retos tras el ensayo")
    args = parser.parse_args()

    flags = None
    if args.apply:
        flags = {
            "ssh": validate_flag("SSH", getpass.getpass("Bandera configurada en DEMO_SSH_FLAG: ")),
            "web": validate_flag("WEB", getpass.getpass("Bandera configurada en DEMO_WEB_FLAG: ")),
        }
    factory = make_session_factory()
    try:
        async with factory() as session:
            result = await configure(session, args.group, flags, apply=args.apply)
            if args.apply:
                await session.commit()
            else:
                await session.rollback()
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await factory.kw["bind"].dispose()


if __name__ == "__main__":
    asyncio.run(main())
