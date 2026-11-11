from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, delete, func, text
from .auth import current, roles, user_view
from .schemas import *
from ..persistence.models import User, Group, Member, Machine, Laboratory, LabMachine, Challenge, Hint, HintUse, Assignment, Run, Ranking, Maintenance, Audit, Completion
from ..persistence.repository import audit, now
from ...application.admin import hasher
from ...domain.laboratory import SCENARIOS, POINTS, LIVE, State, scenario_for, RecursoNoDisponibleError, INSTRUCTIONS

router = APIRouter(prefix="/api/v1")


def public_row(row):
    from sqlalchemy import inspect
    hidden = {"password_hash", "flag_hash", "connection_id"}
    return {a.key: str(value) if isinstance(value, UUID) else value for a in inspect(type(row)).column_attrs if a.key not in hidden for value in [getattr(row, a.key)]}


def enabled(runtime, scenario):
    return scenario.enabled and runtime.settings.ssh_injector_enabled and (scenario.strategy != "DVWA-SQLI-LAB" or runtime.settings.dvwa_lab_enabled)


@router.get("/scenarios")
async def scenarios(request: Request, user=Depends(current)):
    return [{"code": s.code, "strategy": s.strategy, "difficulty": s.difficulty, "points": POINTS[s.difficulty], "victims": s.victims, "enabled": enabled(request.app.state.runtime, s)} for s in SCENARIOS]


@router.get("/users")
async def users(request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions() as s:
        return [user_view(u) for u in (await s.scalars(select(User).order_by(User.username))).all()]


@router.post("/users", status_code=201)
async def add_user(body: NewUser, request: Request, actor=Depends(roles(1))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        user = User(username=body.username, password_hash=hasher.hash(body.password), role=body.role, must_change_password=True)
        s.add(user)
        await s.flush()
        audit(s, "user.created", user.id, actor.id)
        return user_view(user)


async def editable_user(session, user_id):
    target = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if not target: raise HTTPException(404, "Usuario no encontrado")
    if target.role == 1:
        raise HTTPException(409, "La cuenta administradora única está protegida. Cambia su contraseña desde Mi cuenta.")
    if await session.scalar(select(Run.id).where(Run.user_id == user_id, Run.state.in_((*LIVE, State.QUEUED))).limit(1)):
        raise HTTPException(409, "Cierra las corridas del usuario y espera su limpieza antes de modificarlo")
    return target


@router.patch("/users/{user_id}")
async def update_user(user_id: UUID, body: UpdateUser, request: Request, actor=Depends(roles(1))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        target = await editable_user(s, user_id)
        changes = body.model_dump(exclude_unset=True)
        modified = []
        for field in ("username", "role", "state"):
            if field in changes and getattr(target, field) != changes[field]:
                setattr(target, field, changes[field])
                modified.append(field)
        if "password" in changes:
            target.password_hash = hasher.hash(changes["password"])
            target.must_change_password = True
            modified.append("password")
        if modified:
            # Las sesiones existentes no mantienen permisos anteriores.
            target.token_version += 1
            if "role" in modified and target.role != 3:
                await s.execute(delete(Member).where(Member.user_id == user_id))
            audit(s, "user.updated", user_id, actor.id, fields=modified)
        await s.flush()
        return user_view(target)


@router.delete("/users/{user_id}")
async def delete_user(user_id: UUID, body: DeleteUser, request: Request, actor=Depends(roles(1))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        target = await editable_user(s, user_id)
        if body.confirmation != target.username:
            raise HTTPException(422, "Escribe el nombre exacto del usuario para confirmar")
        # No se eliminan en cascada evidencias de aprendizaje ni auditoría.
        references = ((Run, Run.user_id), (Challenge, Challenge.creator_id), (HintUse, HintUse.user_id),
                      (Completion, Completion.user_id), (Ranking, Ranking.user_id), (Audit, Audit.user_id),
                      (Maintenance, Maintenance.resolver_id))
        for model, column in references:
            if await s.scalar(select(func.count()).select_from(model).where(column == user_id)):
                raise HTTPException(409, "El usuario tiene historial. Desactívalo para conservar corridas, puntuaciones y auditoría.")
        await s.execute(delete(Member).where(Member.user_id == user_id))
        audit(s, "user.deleted", user_id, actor.id)
        await s.delete(target)
    return {"ok": True}


@router.get("/groups")
async def groups(request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions() as s:
        return [public_row(g) for g in (await s.scalars(select(Group).order_by(Group.code))).all()]


@router.post("/groups", status_code=201)
async def add_group(body: GroupInput, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        group = Group(code=body.code, name=body.name)
        s.add(group)
        await s.flush()
        for uid in sorted(set(body.users)):
            target = await s.scalar(select(User).where(User.id == uid).with_for_update())
            if not target or target.role != 3 or target.state != "activo": raise HTTPException(422, "Selecciona jugadores activos existentes")
            s.add(Member(group_id=group.id, user_id=uid))
        audit(s, "group.created", group.id, user.id)
        return public_row(group)


@router.get("/machines")
async def machines(request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions() as s:
        occupied = set((await s.scalars(select(Run.attacker_id).where(Run.state.in_(LIVE)))).all()) | set((await s.scalars(select(Run.victim_id).where(Run.state.in_(LIVE)))).all())
        return [{**public_row(vm), "busy": vm.id in occupied, "capacity": 1} for vm in (await s.scalars(select(Machine).order_by(Machine.name))).all()]


@router.patch("/machines/{machine_id}")
async def machine_state(machine_id: UUID, body: MachineState, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(2026110801)"))
        vm = await s.scalar(select(Machine).where(Machine.id == machine_id).with_for_update())
        if not vm: raise HTTPException(404, "Máquina no encontrada")
        if body.state == "ready" and (vm.state == "dirty" or await s.scalar(select(Maintenance.id).where(Maintenance.machine_id == machine_id, Maintenance.state != "confirmado").limit(1))):
            raise HTTPException(409, "Completa la restauración y la prueba de mantenimiento")
        vm.state = body.state
        audit(s, "machine.state", vm.id, user.id, state=body.state)
        return public_row(vm)


@router.get("/laboratories")
async def labs(request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions() as s:
        return [{**public_row(lab), "machines": list((await s.scalars(select(LabMachine.machine_id).where(LabMachine.lab_id == lab.id))).all())} for lab in (await s.scalars(select(Laboratory))).all()]


@router.post("/laboratories", status_code=201)
async def add_lab(body: LabInput, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        lab = Laboratory(code=body.code, name=body.name, segment=body.segment)
        s.add(lab)
        await s.flush()
        vlan = 20 if body.segment.startswith("VLAN20") else 30
        for mid in set(body.machines):
            vm = await s.get(Machine, mid)
            if not vm or vm.vlan != vlan: raise HTTPException(422, "Las máquinas deben pertenecer al segmento elegido")
            s.add(LabMachine(lab_id=lab.id, machine_id=mid))
        audit(s, "laboratory.created", lab.id, user.id)
        return public_row(lab)


@router.patch("/laboratories/{lab_id}")
async def lab_state(lab_id: UUID, body: MachineState, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(2026110801)"))
        lab = await s.get(Laboratory, lab_id)
        if not lab: raise HTTPException(404, "Laboratorio no encontrado")
        if body.state == "ready":
            members = (await s.scalars(select(Machine).join(LabMachine, LabMachine.machine_id == Machine.id).where(LabMachine.lab_id == lab_id))).all()
            if not any(vm.state == "ready" for vm in members): raise HTTPException(409, "Confirma al menos una máquina del laboratorio; solo las ready serán asignables")
        lab.state = body.state
        audit(s, "laboratory.state", lab.id, user.id, state=body.state)
    return {"ok": True}


@router.get("/challenges")
async def challenges(request: Request, user=Depends(current)):
    async with request.app.state.runtime.repo.sessions() as s:
        query = select(Challenge).order_by(Challenge.code)
        if user.role not in (1, 2):
            query = query.join(Assignment, Assignment.challenge_id == Challenge.id).join(Member, Member.group_id == Assignment.group_id).where(Member.user_id == user.id, Challenge.state == "published")
        result = []
        for challenge in (await s.scalars(query)).unique().all():
            busy = await s.scalar(select(Run.id).where(Run.challenge_id == challenge.id, Run.state.in_(LIVE)).limit(1))
            hints = (await s.scalars(select(Hint).where(Hint.challenge_id == challenge.id).order_by(Hint.order))).all()
            group_ids = list((await s.scalars(select(Assignment.group_id).where(Assignment.challenge_id == challenge.id))).all()) if user.role in (1, 2) else []
            result.append({**public_row(challenge), "groups": group_ids, "availability": "en cola" if busy else "disponible", "hints": [{"order": h.order, "penalty": h.penalty} for h in hints]})
        return result


@router.get("/challenges/code-available")
async def code_available(code: str, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions() as s:
        return {"available": not bool(await s.scalar(select(Challenge.id).where(Challenge.code == code)))}


@router.post("/challenges", status_code=201)
async def add_challenge(body: ChallengeInput, request: Request, user=Depends(roles(1, 2))):
    scenario = scenario_for(body.strategy)
    async with request.app.state.runtime.repo.sessions.begin() as s:
        victim = await s.get(Machine, body.victim_id)
        if not victim or victim.kind != "victima" or victim.name not in scenario.victims:
            raise HTTPException(422, "La víctima no corresponde a la estrategia")
        if not await s.scalar(select(LabMachine.id).where(LabMachine.machine_id == victim.id).limit(1)):
            raise HTTPException(422, "Asocia la víctima a un laboratorio primero")
        challenge = Challenge(code=body.code, name=body.name, difficulty=body.difficulty, victim_id=body.victim_id, strategy=body.strategy,
                              points=body.points or POINTS[body.difficulty], mitre=scenario.mitre, description=body.description,
                              instructions=body.instructions or INSTRUCTIONS[scenario.strategy], creator_id=user.id, state="draft", duration_minutes=body.duration_minutes,
                              resources=[resource.model_dump() for resource in body.resources])
        s.add(challenge)
        await s.flush()
        for index, hint in enumerate(body.hints, 1): s.add(Hint(challenge_id=challenge.id, order=index, text=hint.text, penalty=hint.penalty))
        audit(s, "challenge.created", challenge.id, user.id)
        return public_row(challenge)


@router.put("/challenges/{challenge_id}/groups")
async def assign(challenge_id: UUID, body: AssignmentInput, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        if not await s.get(Challenge, challenge_id): raise HTTPException(404, "Reto no encontrado")
        await s.execute(delete(Assignment).where(Assignment.challenge_id == challenge_id))
        for gid in set(body.groups):
            if not await s.get(Group, gid): raise HTTPException(422, "Grupo no encontrado")
            s.add(Assignment(challenge_id=challenge_id, group_id=gid))
        audit(s, "challenge.assigned", challenge_id, user.id)
    return {"ok": True}


@router.post("/challenges/{challenge_id}/pilot")
async def pilot(challenge_id: UUID, request: Request, user=Depends(roles(1, 2))):
    runtime = request.app.state.runtime
    async with runtime.repo.sessions() as s:
        challenge = await s.get(Challenge, challenge_id)
        if not challenge or not enabled(runtime, scenario_for(challenge.strategy)): raise HTTPException(409, "Integración deshabilitada; valida los helpers primero")
    return public_row(await runtime.repo.enqueue(user.id, challenge_id, pilot=True))


@router.post("/challenges/{challenge_id}/publish")
async def publish(challenge_id: UUID, request: Request, user=Depends(roles(1, 2))):
    runtime = request.app.state.runtime
    async with runtime.repo.sessions.begin() as s:
        challenge = await s.scalar(select(Challenge).where(Challenge.id == challenge_id).with_for_update())
        if not challenge or not challenge.pilot_passed: raise HTTPException(409, "Requiere una prueba piloto con limpieza exitosa")
        if not enabled(runtime, scenario_for(challenge.strategy)): raise HTTPException(409, "Estrategia deshabilitada")
        if not await s.scalar(select(Assignment.id).where(Assignment.challenge_id == challenge_id).limit(1)):
            raise HTTPException(409, "Asigna el reto a un grupo primero")
        challenge.state = "published"
        audit(s, "challenge.published", challenge_id, user.id)
    return {"ok": True}


@router.post("/challenges/{challenge_id}/start", status_code=202)
async def start(challenge_id: UUID, request: Request, user=Depends(roles(3))):
    runtime = request.app.state.runtime
    async with runtime.repo.sessions() as s:
        challenge = await s.get(Challenge, challenge_id)
        if not challenge or not enabled(runtime, scenario_for(challenge.strategy)): raise HTTPException(409, "Estrategia deshabilitada")
    return public_row(await runtime.repo.enqueue(user.id, challenge_id))


@router.get("/runs")
async def runs(request: Request, user=Depends(current)):
    async with request.app.state.runtime.repo.sessions() as s:
        query = select(Run).order_by(Run.started.desc()).limit(100)
        if user.role not in (1, 2): query = query.where(Run.user_id == user.id)
        return [public_row(r) for r in (await s.scalars(query)).all()]


@router.post("/runs/{run_id}/flag")
async def submit(run_id: str, body: FlagInput, request: Request, user=Depends(roles(3))):
    runtime = request.app.state.runtime
    if not await runtime.cache.login_attempt(f"flag:{user.id}"): raise HTTPException(429, "Espera un minuto antes de otro intento")
    return await runtime.repo.submit(run_id, user.id, body.flag)


@router.post("/runs/{run_id}/hints/{order}")
async def hint(run_id: str, order: int, request: Request, user=Depends(roles(3))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        run = await s.scalar(select(Run).where(Run.id == run_id, Run.user_id == user.id).with_for_update())
        if not run or run.state != State.ACTIVE or run.expires <= now(): raise HTTPException(409, "Corrida no activa")
        item = await s.scalar(select(Hint).where(Hint.challenge_id == run.challenge_id, Hint.order == order))
        if not item: raise HTTPException(404, "Pista no encontrada")
        from sqlalchemy.dialects.postgresql import insert
        await s.execute(insert(HintUse).values(user_id=user.id, challenge_id=run.challenge_id, hint_id=item.id, penalty=item.penalty).on_conflict_do_nothing())
        audit(s, "hint.revealed", run_id, user.id, order=order)
        return {"text": item.text, "penalty": item.penalty}


@router.post("/runs/{run_id}/close")
async def close(run_id: str, request: Request, user=Depends(current)):
    runtime = request.app.state.runtime
    run, _, _, _ = await runtime.repo.context(run_id)
    if run.user_id != user.id and user.role not in (1, 2): raise HTTPException(404, "Corrida no encontrada")
    await runtime.repo.cleaning(run_id, State.CANCELLED)
    return {"ok": True}


@router.get("/ranking")
async def ranking(request: Request, user=Depends(current)):
    async with request.app.state.runtime.repo.sessions() as s:
        rows = (await s.execute(select(User.username, Ranking.points, Ranking.completed).join(User, User.id == Ranking.user_id).order_by(Ranking.points.desc(), Ranking.updated, User.username))).all()
        return [{"username": row.username, "points": row.points, "completed": row.completed} for row in rows]


@router.get("/maintenance")
async def maintenance(request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions() as s:
        return [public_row(m) for m in (await s.scalars(select(Maintenance).order_by(Maintenance.created.desc()))).all()]


@router.post("/maintenance")
async def request_maintenance(body: MaintenanceInput, request: Request, user=Depends(roles(1, 2))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(2026110801)"))
        vm = await s.get(Machine, body.machine_id)
        if not vm: raise HTTPException(404, "Máquina no encontrada")
        existing = await s.scalar(select(Maintenance).where(Maintenance.machine_id == vm.id, Maintenance.state != "confirmado").limit(1))
        if existing: return public_row(existing)
        vm.state = "mantenimiento"
        item = Maintenance(machine_id=vm.id, reason=body.reason)
        s.add(item)
        await s.flush()
        audit(s, "maintenance.requested", item.id, user.id)
        return public_row(item)


@router.post("/maintenance/{maintenance_id}/confirm")
async def confirm_maintenance(maintenance_id: UUID, request: Request, user=Depends(roles(1))):
    async with request.app.state.runtime.repo.sessions.begin() as s:
        item = await s.scalar(select(Maintenance).where(Maintenance.id == maintenance_id).with_for_update())
        if not item or not item.tested: raise HTTPException(409, "Ejecuta la prueba posterior a la restauración por consola")
        busy = await s.scalar(select(Run.id).where(((Run.victim_id == item.machine_id) | (Run.attacker_id == item.machine_id)), Run.state.in_(LIVE)).limit(1))
        if busy: raise HTTPException(409, "Todavía hay corridas por limpiar")
        item.state, item.resolved, item.resolver_id = "confirmado", now(), user.id
        vm = await s.get(Machine, item.machine_id)
        vm.state = "ready"
        audit(s, "maintenance.confirmed", item.id, user.id)
    return {"ok": True}
