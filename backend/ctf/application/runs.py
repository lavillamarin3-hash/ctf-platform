import secrets
from ..domain.laboratory import State, flag_hash, new_flag, scenario_for, RecursoNoDisponibleError


class RunService:
    def __init__(self, repository, injector, terminal, cache):
        self.repo, self.injector, self.terminal, self.cache = repository, injector, terminal, cache

    async def provision(self, run_id):
        run, challenge, victim, attacker = await self.repo.context(run_id)
        scenario = scenario_for(challenge.strategy)
        if not scenario.enabled or not scenario.script or not attacker:
            await self.repo.cleaning(run_id, State.CANCELLED)
            raise RecursoNoDisponibleError()
        flag = new_flag(scenario.strategy)
        expected = flag_hash(flag)
        password = secrets.token_urlsafe(32)
        try:
            # PostgreSQL ya confirmó la reserva. Redis es complementario.
            await self.cache.lock(run)
            await self.injector.execute(str(victim.ip), scenario.script, "create", run_id, flag)
            result = await self.injector.execute(str(victim.ip), scenario.script, "check", run_id)
            if result.get("flag_hash") != expected: raise RecursoNoDisponibleError()
            await self.injector.execute(str(attacker.ip), "/usr/local/sbin/ctf-kali-session", "create", run_id, password)
            await self.injector.verify_session(str(attacker.ip), run_id, password)
            connection_id = await self.terminal.create(run_id, str(attacker.ip), password)
            await self.repo.activate(run_id, expected, connection_id)
            if run.pilot:
                await self.repo.submit(run_id, run.user_id, flag)
                await self.cleanup(run_id)
        except Exception:
            await self.repo.cleaning(run_id, State.CANCELLED)
            await self.repo.error(run_id, "PROVISION_FAILED")
            # Incluso si create perdió su respuesta, destruir todos los recursos
            # deterministas. Si falla, la reserva persiste para reintento.
            await self.cleanup(run_id)
            raise RecursoNoDisponibleError() from None

    async def cleanup(self, run_id):
        run, challenge, victim, attacker = await self.repo.context(run_id)
        if run.state == State.RELEASED: return
        scenario = scenario_for(challenge.strategy)
        failures = []
        operations = [lambda: self.terminal.destroy(run_id)]
        if attacker:
            operations.append(lambda: self.injector.execute(str(attacker.ip), "/usr/local/sbin/ctf-kali-session", "destroy", run_id))
        if scenario.script:
            operations.append(lambda: self.injector.execute(str(victim.ip), scenario.script, "destroy", run_id))
        for operation in operations:
            try: await operation()
            except Exception: failures.append(True)
        if failures:
            await self.repo.error(run_id, "CLEANUP_PENDING")
            raise RecursoNoDisponibleError()
        await self.cache.unlock(run)
        await self.repo.released(run_id)
