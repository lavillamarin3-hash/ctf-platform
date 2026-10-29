"""Preparación OPT-IN del reto SSH existente ESC-02 en CoCiber CTF.

Por defecto únicamente informa el plan. No crea conexiones Guacamole, no
instala programas en la víctima y no modifica cuentas ni puntajes históricos.

Comando (en el contenedor API):
  python configure_ssh_access_challenge.py --group GRP-PILOTO-01 --attacker LAB-KALI-BLUE
  python configure_ssh_access_challenge.py --group GRP-PILOTO-01 --attacker LAB-KALI-BLUE --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import make_session_factory
from app.models import (
    Challenge, ChallengeFlag, ChallengeGroupAssignment, ChallengeRun,
    Laboratory, StudentGroup, VMAsset,
)

CODE = "ESC-02-BRUTEFORCE"
SCENARIO = "SSH-PASSWORD-LAB"
VICTIM = ("LAB-LNXVICT", "10.10.30.12")
ATTACKERS = {
    "LAB-KALI": "10.10.20.10",
    "LAB-KALI-PURPLE": "10.10.20.11",
    "LAB-KALI-BLUE": "10.10.20.12",
}
TEMPLATE = "FLAG{ssh_practice_{{RAND}}}"


async def prepare(session, group_code: str, attacker_name: str, *, apply: bool = False):
    attacker_ip = ATTACKERS[attacker_name]
    group = await session.scalar(select(StudentGroup).where(
        StudentGroup.code == group_code, StudentGroup.is_active.is_(True)
    ))
    if group is None:
        raise ValueError("El grupo indicado no existe o está inactivo; regístralo y añade estudiantes antes.")
    vm_rows = (await session.scalars(select(VMAsset).where(
        VMAsset.ip_address.in_((VICTIM[1], attacker_ip))
    ))).all()
    labs = (await session.scalars(select(Laboratory))).all()
    targets = {}
    for name, ip in (VICTIM, (attacker_name, attacker_ip)):
        matches = [vm for vm in vm_rows if vm.ip_address == ip]
        if len(matches) != 1 or matches[0].name != name:
            raise ValueError(f"Inventario incorrecto: {name} debe existir una sola vez con IP {ip}.")
        vm = matches[0]
        lab = next((item for item in labs if item.id == vm.laboratory_id), None)
        if vm.status != "ready" or lab is None or lab.status != "ready":
            raise ValueError(f"{name} y su laboratorio deben estar ready tras comprobar una conexión real.")
        if name == VICTIM[0] and not any(token in vm.os.lower() for token in ("ubuntu", "linux")):
            raise ValueError("LAB-LNXVICT debe ser Linux/Ubuntu, nunca Kali atacante.")
        targets[name] = vm.id

    challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags))
        .where(Challenge.code == CODE).with_for_update())
    desired = [attacker_name, VICTIM[0]]
    modifications = []
    if challenge is None:
        modifications.append("Crear reto ESC-02 en borrador con una única bandera dinámica")
    else:
        if challenge.scenario != SCENARIO or challenge.asset_references != desired:
            modifications.append("Corregir escenario y activos del reto existente")
        active = [flag for flag in challenge.flags if flag.is_active]
        if not active:
            modifications.append("Agregar bandera dinámica al reto existente sin eliminar las antiguas")
        elif len(active) != 1 or active[0].mode != "dynamic" or not active[0].template:
            raise ValueError("Existen banderas activas incompatibles. Revísalas manualmente; no se reemplazarán.")
        if modifications:
            running = await session.scalar(select(ChallengeRun.id).where(
                ChallengeRun.challenge_id == challenge.id,
                ChallengeRun.status.not_in(("closed", "expired"))
            ).limit(1))
            if running is not None:
                raise ValueError("Hay una corrida pendiente o activa; ciérrala correctamente antes de editar.")

    if challenge is not None:
        assigned = await session.scalar(select(ChallengeGroupAssignment.id).where(
            ChallengeGroupAssignment.group_id == group.id,
            ChallengeGroupAssignment.challenge_id == challenge.id))
    else:
        assigned = None
    if assigned is None:
        modifications.append("Asignar el reto al grupo existente")

    report = {
        "applied": apply,
        "challenge": CODE, "attacker": attacker_name,
        "victim": VICTIM[0], "group": group_code, "vm_ids": targets,
        "existing_challenge": challenge is not None, "changes": modifications,
        "published": challenge.is_published if challenge is not None else False,
        "note": "No se crean conexiones SSH/RDP ni se publica automáticamente un reto nuevo.",
    }
    if not apply:
        await session.rollback()
        return report

    if challenge is None:
        challenge = Challenge(
            code=CODE, name="Práctica SSH: recuperación de bandera dinámica",
            description=("Desde una Kali autorizada investiga el servicio SSH didáctico "
                         "de LAB-LNXVICT, recupera una bandera individual y envíala."),
            instructions=("Inicia el reto y abre la consola SSH o RDP de tu Kali. "
                          "Obtén el usuario y diccionario de 12 candidatos en la pantalla. "
                          "Prueba únicamente el servicio de LAB-LNXVICT 10.10.30.12:2222. "
                          "Una vez identificada la contraseña temporal, conéctate por SSH "
                          "a ese puerto, ejecuta cat flag.txt y envía la bandera. "
                          "Cierra la corrida para invalidar la cuenta temporal."),
            difficulty="Medio", category="REDES", scenario=SCENARIO,
            mitre_technique="T1110.001 — Password Guessing",
            asset_references=desired, points=250, is_published=False,
            learning_policy=None,
        )
        session.add(challenge)
        await session.flush()
    else:
        challenge.scenario = SCENARIO
        challenge.asset_references = desired

    if not any(flag.is_active for flag in challenge.flags):
        session.add(ChallengeFlag(
            challenge_id=challenge.id, label="Bandera SSH dinámica por corrida",
            mode="dynamic", template=TEMPLATE, flag_order=1, is_active=True,
            flag_hash=None,
        ))
    if assigned is None:
        session.add(ChallengeGroupAssignment(
            challenge_id=challenge.id, group_id=group.id,
        ))
    await session.commit()
    return report


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", required=True, help="Código de grupo existente y activo")
    parser.add_argument("--attacker", choices=sorted(ATTACKERS), default="LAB-KALI-BLUE")
    parser.add_argument("--apply", action="store_true", help="Aplicar cambios después de revisar el plan")
    args = parser.parse_args()
    factory = make_session_factory()
    try:
        async with factory() as session:
            result = await prepare(session, args.group, args.attacker, apply=args.apply)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await factory.kw["bind"].dispose()


if __name__ == "__main__":
    asyncio.run(main())
