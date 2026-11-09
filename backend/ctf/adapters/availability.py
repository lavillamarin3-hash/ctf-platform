"""Reintenta solo sondas de lectura, nunca reproduce una escritura o inyección."""
import asyncio
from time import monotonic
from sqlalchemy import text
from ..domain.laboratory import RecursoNoDisponibleError


class AvailabilityGate:
    def __init__(self, repository, cache):
        self.repo, self.cache = repository, cache
        self.checked_until = 0.0
        self.open_until = 0.0
        self.lock = asyncio.Lock()
        self.status = {"postgres": False, "redis": False}

    async def probe(self, action):
        for attempt in range(3):
            try:
                async with asyncio.timeout(2): await action()
                return True
            except Exception:
                if attempt < 2: await asyncio.sleep(0.1 * 2 ** attempt)
        return False

    async def check(self):
        async with self.lock:
            if monotonic() < self.open_until: raise RecursoNoDisponibleError()
            if monotonic() < self.checked_until: return self.status
            async def postgres():
                async with self.repo.sessions() as s:
                    await s.execute(text('SELECT usu_id FROM "USUARIOS" LIMIT 0'))
            pg, redis = await asyncio.gather(self.probe(postgres), self.probe(self.cache.client.ping))
            self.status = {"postgres": pg, "redis": redis}
            if not (pg and redis):
                self.open_until = monotonic() + 10
                raise RecursoNoDisponibleError()
            self.checked_until = monotonic() + 2
            return self.status
