"""Auditoría y actualización opt-in del inventario AHV. Por defecto NO escribe.

Solo actualiza fichas inequívocas sin sesiones activas ni instancias ocupadas.
No cambia Guacamole, flags, retos ni snapshots. Requiere backup antes --apply.
"""
import argparse
import asyncio
import json

from sqlalchemy import select, func
from app.db import make_session_factory
from app.models import Laboratory, VMAsset, ChallengeInstance
from app.domain.challenges.catalog import OPERATIONAL_VM_TARGETS

ATTACKERS = {"LAB-KALI", "LAB-KALI-BLUE", "LAB-KALI-PURPLE"}
OLD_IPS = {"LAB-KALI": "192.168.146.134", "LAB-LNXVICT": "192.168.146.137"}


async def audit(session):
    rows = list((await session.scalars(select(VMAsset).order_by(VMAsset.id).with_for_update())).all())
    labs = {lab.id: lab for lab in (await session.scalars(select(Laboratory))).all()}
    names = {}
    ip_owners = {}
    for vm in rows:
        names.setdefault(vm.name.upper(), []).append(vm)
        if vm.ip_address:
            ip_owners.setdefault(vm.ip_address, []).append(vm)
    plan = []
    blockers = []
    for name, target in OPERATIONAL_VM_TARGETS.items():
        matches = names.get(name, [])
        if len(matches) > 1:
            blockers.append(f"{name}: hay fichas duplicadas; corregir manualmente")
            continue
        if not matches:
            plan.append({"vm": name, "action": "missing", "ip": target,
                         "note": "Crear desde el panel administrativo, no automáticamente"})
            continue
        vm = matches[0]
        if vm.ip_address == target:
            plan.append({"vm": name, "action": "unchanged", "ip": target})
            continue
        if vm.ip_address not in (None, OLD_IPS.get(name)):
            blockers.append(f"{name}: IP actual inesperada; no se sobrescribe")
            continue
        if any(owner.id != vm.id for owner in ip_owners.get(target, [])):
            blockers.append(f"{name}: IP destino ocupada por otra ficha")
            continue
        count = await session.scalar(select(func.count(ChallengeInstance.id)).where(
            ChallengeInstance.vm_asset_id == vm.id,
            ChallengeInstance.run_id.is_not(None)))
        if count:
            blockers.append(f"{name}: tiene una instancia asignada")
            continue
        plan.append({"vm": name, "action": "update", "id": vm.id,
                     "old_ip": vm.ip_address, "ip": target})
    return plan, blockers, names, labs


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Aplicar únicamente cambios revisados previamente")
    parser.add_argument("--fresh", action="store_true", help="Usar el esquema nuevo, sin leer ni migrar el histórico")
    args = parser.parse_args()
    if args.fresh:
        await reconcile_fresh(args.apply)
        return
    factory = make_session_factory()
    try:
        async with factory() as session:
            plan, blockers, names, labs = await audit(session)
            updates = [p for p in plan if p["action"] == "update"]
            if args.apply and blockers:
                await session.rollback()
                raise SystemExit("Bloqueado por conflictos de inventario. Corrige antes de aplicar. " + "; ".join(blockers))
            if args.apply:
                for row in updates:
                    vm = names[row["vm"]][0]
                    lab = labs.get(vm.laboratory_id)
                    is_attacker = row["vm"] in ATTACKERS
                    expected_segment = "VLAN 20" if is_attacker else "VLAN 30"
                    if lab is None:
                        raise SystemExit("Laboratorio asociado inexistente")
                    # Solo actualizar metadatos de esta ficha: no tocar conexiones o IDs AHV.
                    vm.ip_address = row["ip"]
                    vm.vlan = expected_segment
                    vm.network_role = "Atacantes" if is_attacker else "Víctimas"
                    vm.subnet = "10.10.20.0/24" if is_attacker else "10.10.30.0/24"
                    # La VM permanece planificada hasta que un admin valide Guacamole.
                    vm.status = "planned"
                await session.commit()
            else:
                await session.rollback()
            print(json.dumps({"applied": args.apply, "updates": len(updates),
                              "plan": plan, "blockers": blockers}, ensure_ascii=False, indent=2))
    finally:
        await factory.kw["bind"].dispose()


async def reconcile_fresh(apply=False):
    """Mismo catálogo confirmado, fichas planned; no declara validación de Prism."""
    from ctf.infrastructure.settings import settings
    from ctf.adapters.persistence.repository import Repository, audit as fresh_audit
    from ctf.adapters.persistence.models import Machine
    repo = Repository(settings().database_url)
    try:
        async with repo.sessions.begin() as session:
            rows = (await session.scalars(select(Machine).with_for_update())).all()
            plan, blockers = [], []
            for name, ip in OPERATIONAL_VM_TARGETS.items():
                vm = next((row for row in rows if row.name == name), None)
                if vm and str(vm.ip) != ip:
                    blockers.append(f"{name}: IP distinta; revisar manualmente")
                elif any(str(row.ip) == ip and row.name != name for row in rows):
                    blockers.append(f"{name}: IP ocupada por otra ficha")
                elif not vm:
                    plan.append({"name": name, "ip": ip, "state": "planned"})
            if apply and blockers: raise ValueError("Hay conflictos; no se cambia el inventario")
            if apply:
                for item in plan:
                    attacker = item["name"] in ATTACKERS
                    session.add(Machine(name=item["name"], ip=item["ip"], state="planned", kind="atacante" if attacker else "victima", vlan=20 if attacker else 30,
                                        os="Windows" if "WINVICT" in item["name"] else "Linux"))
                fresh_audit(session, "inventory.reconciled", "catalog", added=len(plan))
            print(json.dumps({"applied": apply, "source": "catálogo confirmado; NO consulta Prism", "plan": plan, "blockers": blockers}, ensure_ascii=False, indent=2))
    finally: await repo.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
