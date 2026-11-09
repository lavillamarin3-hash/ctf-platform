"""Administración fuera de la web: python -m ctf.infrastructure.cli --help."""
import argparse
import asyncio
import getpass
import secrets
from uuid import UUID
from sqlalchemy import select, text
from .runtime import Runtime
from ..adapters.persistence.models import Base, Role, User, Machine, Run, Maintenance, Challenge, Laboratory, LabMachine
from ..application.admin import create_first_admin
from ..domain.laboratory import LIVE, scenario_for, new_flag, flag_hash


async def execute(args):
    runtime = Runtime()
    try:
        if args.command == "init-db":
            if not args.empty_database: raise ValueError("Requiere --empty-database")
            async with runtime.repo.engine.begin() as connection:
                tables = await connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"))
                if tables: raise ValueError("La base contiene tablas. Usa una base NUEVA; no se borrará nada")
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
                await connection.run_sync(Base.metadata.create_all)
            async with runtime.repo.sessions.begin() as s:
                for rid, name in enumerate(("administrador", "instructor", "player", "invitado"), 1): s.add(Role(id=rid, name=name))
            print("Esquema nuevo creado; sin usuarios, inventario ni retos de prueba automáticos.")
        elif args.command == "create-admin":
            password = runtime.settings.admin_ctf_password.get_secret_value() or getpass.getpass("Contraseña inicial: ")
            await create_first_admin(runtime.repo, runtime.settings.admin_ctf_username, password)
            print("Administrador creado; cambio de contraseña obligatorio al entrar.")
        elif args.command == "check":
            async with runtime.repo.sessions() as s: await s.execute(text('SELECT usu_id FROM "USUARIOS" LIMIT 0'))
            await runtime.cache.client.ping()
            print("PostgreSQL y Redis: OK")
        elif args.command == "configure-catalog":
            from ..application.catalog import drafts
            from ..adapters.persistence.repository import audit
            async with runtime.repo.sessions.begin() as s:
                machines = list((await s.scalars(select(Machine))).all())
                for kind, vlan, code, name in (("atacante",20,"LAB-ATACANTES","Laboratorio de atacantes"),("victima",30,"LAB-VICTIMAS","Laboratorio de víctimas")):
                    lab = await s.scalar(select(Laboratory).where(Laboratory.code == code))
                    if not lab and args.apply:
                        lab = Laboratory(code=code, name=name, segment=f"VLAN{vlan}-10.10.{vlan}.0/24", state="planned")
                        s.add(lab)
                        await s.flush()
                    if args.apply and lab:
                        for vm in machines:
                            if vm.kind == kind and not await s.scalar(select(LabMachine.id).where(LabMachine.lab_id == lab.id, LabMachine.machine_id == vm.id)):
                                s.add(LabMachine(lab_id=lab.id, machine_id=vm.id))
                for draft in drafts():
                    existing = await s.scalar(select(Challenge).where(Challenge.code == draft["code"]))
                    victim = next((vm for vm in machines if vm.name == draft["victim"]), None)
                    if not victim: raise ValueError("Conciliar el inventario antes de configurar el catálogo")
                    if existing:
                        if existing.strategy != draft["strategy"] or existing.victim_id != victim.id:
                            raise ValueError("Reto existente incompatible; no se sobrescribe")
                        print(f"{draft['code']}: existente; conservado")
                        continue
                    print(f"{draft['code']}: borrador; " + ("integración opt-in" if draft["implementation_available"] else "pendiente, deshabilitado"))
                    if args.apply:
                        s.add(Challenge(**{k:v for k,v in draft.items() if k not in ("victim", "implementation_available")}, victim_id=victim.id, state="draft", description=draft["name"]))
                if args.apply: audit(s, "catalog.configured", "fresh")
            print("Aplicado" if args.apply else "Diagnóstico sin cambios; usa --apply para crear los borradores")
        elif args.command == "test-injector":
            scenario = scenario_for(args.scenario)
            if not scenario.enabled or not scenario.script: raise ValueError("Contrato de escenario pendiente; no se ejecutará")
            async with runtime.repo.sessions.begin() as s:
                await s.execute(text("SELECT pg_advisory_xact_lock(2026110801)"))
                vm = await s.scalar(select(Machine).where(Machine.name == args.machine).with_for_update())
                if not vm or vm.name not in scenario.victims: raise ValueError("Máquina/escenario no corresponden")
                if await s.scalar(select(Run.id).where((Run.victim_id == vm.id) | (Run.attacker_id == vm.id), Run.state.in_(LIVE)).limit(1)):
                    raise ValueError("Hay corridas vivas: drena primero")
                # Drenar antes de tocar un helper; no reactivar automáticamente.
                vm.state = "mantenimiento"
                host, vm_id = str(vm.ip), vm.id
            # Este comando explícito permite probar sin habilitar globalmente.
            runtime.injector.settings = runtime.settings.model_copy(update={"ssh_injector_enabled": True, "dvwa_lab_enabled": True})
            run_id = secrets.token_hex(6)
            flag = new_flag(scenario.strategy)
            try:
                await runtime.injector.execute(host, scenario.script, "create", run_id, flag)
                result = await runtime.injector.execute(host, scenario.script, "check", run_id)
                if result.get("flag_hash") != flag_hash(flag): raise ValueError("El helper no verificó la evidencia")
            finally:
                await runtime.injector.execute(host, scenario.script, "destroy", run_id)
            async with runtime.repo.sessions.begin() as s:
                pending = (await s.scalars(select(Maintenance).where(Maintenance.machine_id == vm_id, Maintenance.state != "confirmado"))).all()
                for item in pending: item.tested = True
            print("create → check → destroy: OK. La máquina sigue en mantenimiento hasta confirmación administrativa.")
    finally: await runtime.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-db")
    init.add_argument("--empty-database", action="store_true")
    commands.add_parser("create-admin")
    commands.add_parser("check")
    catalog = commands.add_parser("configure-catalog")
    catalog.add_argument("--apply", action="store_true")
    test = commands.add_parser("test-injector")
    test.add_argument("machine")
    test.add_argument("scenario")
    try: asyncio.run(execute(parser.parse_args()))
    except ValueError as exc: raise SystemExit(str(exc)) from None
    except Exception: raise SystemExit("Operación no completada; revisa dependencias y configuración privada. No se muestran credenciales.") from None


if __name__ == "__main__": main()
