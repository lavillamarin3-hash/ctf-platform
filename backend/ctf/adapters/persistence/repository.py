"""Transacciones cortas. No mantener locks PostgreSQL durante operaciones remotas."""
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert
from .models import *
from ...domain.laboratory import LIVE, State, CorridaYaActivaError, RecursoNoDisponibleError, flag_hash, verify_flag


def now(): return datetime.now(timezone.utc)


def audit(session, action, entity_id, user_id=None, **details):
    session.add(Audit(user_id=user_id, action=action, entity="ctf", entity_id=str(entity_id), details=details))


class Repository:
    def __init__(self, url):
        self.engine = create_async_engine(url, pool_pre_ping=True, connect_args={"timeout": 5, "command_timeout": 15})
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def admin_exists(self):
        async with self.sessions() as session:
            return bool(await session.scalar(select(User.id).where(User.role == 1).limit(1)))

    async def create_first_admin(self, username, hashed_password):
        async with self.sessions.begin() as session:
            await session.execute(text("SELECT pg_advisory_xact_lock(2026110802)"))
            if await session.scalar(select(User.id).where(User.role == 1).limit(1)):
                raise ValueError("Ya existe un administrador; el bootstrap no crea otro")
            user = User(username=username, password_hash=hashed_password, role=1, must_change_password=True)
            session.add(user)
            await session.flush()
            audit(session, "admin.bootstrap", user.id, user.id)

    async def context(self, run_id):
        async with self.sessions() as s:
            run = await s.get(Run, run_id)
            if not run: raise RecursoNoDisponibleError()
            challenge = await s.get(Challenge, run.challenge_id)
            victim = await s.get(Machine, run.victim_id)
            attacker = await s.get(Machine, run.attacker_id) if run.attacker_id else None
            return run, challenge, victim, attacker

    async def enqueue(self, user_id, challenge_id, *, pilot=False):
        async with self.sessions.begin() as s:
            # Comparte el bloqueo con la gestión de usuarios: no admitir una
            # corrida entre la comprobación de actividad y un cambio de rol/baja.
            user = await s.scalar(select(User).where(User.id == user_id).with_for_update())
            if not user or user.state != "activo" or user.role not in ((1, 2) if pilot else (3,)):
                raise RecursoNoDisponibleError()
            challenge = await s.scalar(select(Challenge).where(Challenge.id == challenge_id).with_for_update())
            if not challenge or (not pilot and challenge.state != "published"):
                raise RecursoNoDisponibleError()
            if not pilot:
                member = await s.scalar(select(Member.id).join(Assignment, Assignment.group_id == Member.group_id).where(Member.user_id == user_id, Assignment.challenge_id == challenge.id).limit(1))
                if not member: raise RecursoNoDisponibleError()
            existing = await s.scalar(select(Run).where(Run.user_id == user_id, Run.challenge_id == challenge_id, Run.state.in_((*LIVE, State.QUEUED))))
            if existing: return existing
            run = Run(id=secrets.token_hex(6), user_id=user_id, challenge_id=challenge_id, victim_id=challenge.victim_id,
                      expires=now() + timedelta(hours=4), state=State.QUEUED, pilot=pilot)
            s.add(run)
            audit(s, "run.queued", run.id, user_id)
            return run

    async def reserve_next(self, ttl_by_difficulty):
        async with self.sessions.begin() as s:
            # Serializa elección entre procesos. Los índices son la defensa definitiva.
            await s.execute(text("SELECT pg_advisory_xact_lock(2026110801)"))
            queue = list((await s.scalars(select(Run).where(Run.state == State.QUEUED).order_by(Run.started).limit(100).with_for_update())).all())
            occupied = list((await s.scalars(select(Run).where(Run.state.in_(LIVE)))).all())
            for run in queue:
                if run.expires < now():
                    run.state, run.outcome = State.RELEASED, State.EXPIRED
                    continue
                challenge = await s.get(Challenge, run.challenge_id)
                victim = await s.get(Machine, run.victim_id)
                if not run.pilot:
                    assigned = await s.scalar(select(Member.id).join(Assignment, Assignment.group_id == Member.group_id).where(Member.user_id == run.user_id, Assignment.challenge_id == challenge.id).limit(1))
                    if not assigned or challenge.state != "published":
                        run.state, run.outcome = State.RELEASED, State.CANCELLED
                        continue
                if any(r.challenge_id == run.challenge_id or r.victim_id == run.victim_id for r in occupied): continue
                if victim.state != "ready": continue
                if not await s.scalar(select(LabMachine.id).join(Laboratory, Laboratory.id == LabMachine.lab_id).where(LabMachine.machine_id == victim.id, Laboratory.state == "ready").limit(1)): continue
                attackers = (await s.scalars(select(Machine).join(LabMachine, LabMachine.machine_id == Machine.id).join(Laboratory, Laboratory.id == LabMachine.lab_id).where(Machine.kind == "atacante", Machine.state == "ready", Laboratory.state == "ready").order_by(Machine.name))).unique().all()
                attacker = next((vm for vm in attackers if not any(r.attacker_id == vm.id for r in occupied)), None)
                if not attacker: continue
                run.attacker_id = attacker.id
                run.state = State.RESERVED
                run.expires = now() + timedelta(minutes=challenge.duration_minutes or ttl_by_difficulty[challenge.difficulty])
                audit(s, "run.reserved", run.id, run.user_id)
                return run.id
        return None

    async def activate(self, run_id, hashed_flag, connection_id):
        async with self.sessions.begin() as s:
            run = await s.scalar(select(Run).where(Run.id == run_id).with_for_update())
            if run.state != State.RESERVED: raise CorridaYaActivaError()
            run.flag_hash, run.connection_id, run.state = hashed_flag, connection_id, State.ACTIVE
            audit(s, "run.active", run_id, run.user_id)

    async def cleaning(self, run_id, outcome):
        async with self.sessions.begin() as s:
            run = await s.scalar(select(Run).where(Run.id == run_id).with_for_update())
            if run.state == State.RELEASED: return
            if run.state == State.QUEUED:
                run.state, run.outcome, run.finished = State.RELEASED, outcome, now()
            else:
                run.state = State.CLEANING
                run.outcome = run.outcome or outcome
            audit(s, "run.cleanup_requested", run_id, run.user_id)

    async def released(self, run_id):
        async with self.sessions.begin() as s:
            run = await s.scalar(select(Run).where(Run.id == run_id).with_for_update())
            if run.state != State.CLEANING: raise CorridaYaActivaError()
            run.state, run.finished = State.RELEASED, now()
            challenge = await s.get(Challenge, run.challenge_id)
            if run.pilot and run.outcome == State.SOLVED:
                challenge.pilot_passed = True
            # Política conservadora: DVWA/Windows esperan restauración manual.
            if not run.pilot and challenge.strategy in ("DVWA-SQLI-LAB", "LATERAL-SMB-LAB"):
                vm = await s.get(Machine, run.victim_id)
                vm.state = "dirty"
                s.add(Maintenance(machine_id=vm.id, reason=f"Restauración tras {challenge.code}; corrida {run.id}"))
            audit(s, "run.released", run_id, run.user_id, outcome=run.outcome)

    async def submit(self, run_id, user_id, value):
        async with self.sessions.begin() as s:
            run = await s.scalar(select(Run).where(Run.id == run_id, Run.user_id == user_id).with_for_update())
            if not run or run.state != State.ACTIVE or run.expires <= now(): raise RecursoNoDisponibleError()
            correct = verify_flag(value, run.flag_hash)
            s.add(Attempt(run_id=run.id, value_hash=flag_hash(value.strip()), correct=correct))
            awarded = 0
            if correct:
                challenge = await s.get(Challenge, run.challenge_id)
                if not run.pilot:
                    penalty = await s.scalar(select(func.coalesce(func.sum(HintUse.penalty), 0)).where(HintUse.user_id == user_id, HintUse.challenge_id == challenge.id))
                    final_points = max(0, challenge.points - int(penalty))
                    result = await s.execute(insert(Completion).values(id=secrets_uuid(), user_id=user_id, challenge_id=challenge.id, points=final_points).on_conflict_do_nothing().returning(Completion.id))
                    if result.scalar_one_or_none():
                        awarded = final_points
                        await s.execute(insert(Ranking).values(user_id=user_id, points=awarded, completed=1).on_conflict_do_update(index_elements=[Ranking.user_id], set_={Ranking.points: Ranking.points + awarded, Ranking.completed: Ranking.completed + 1, Ranking.updated: now()}))
                run.state, run.outcome = State.CLEANING, State.SOLVED
            audit(s, "flag.submitted", run_id, user_id, correct=correct, points=awarded)
            return {"correct": correct, "points": awarded}

    async def error(self, run_id, code):
        async with self.sessions.begin() as s:
            audit(s, "run.error", run_id, error_code=code)


def secrets_uuid():
    from uuid import uuid4
    return uuid4()
