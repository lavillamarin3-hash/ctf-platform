"""Un proceso externo; advisory lock de sesión impide un segundo worker."""
import argparse
import asyncio
import logging
from sqlalchemy import select, text
from .runtime import Runtime
from ..adapters.persistence.models import Run, Ranking
from ..adapters.persistence.repository import now
from ..domain.laboratory import State


async def tick(runtime):
    async with runtime.repo.sessions() as s:
        pending = (await s.scalars(select(Run).where(Run.state.in_((State.RESERVED, State.CLEANING, State.ACTIVE))).order_by(Run.started))).all()
    for run in pending:
        try:
            # Una reserva encontrada al comenzar tick proviene de un proceso
            # interrumpido: compensar antes de asignar cualquier recurso nuevo.
            if run.state == State.RESERVED:
                await runtime.repo.cleaning(run.id, State.CANCELLED)
                await runtime.runs.cleanup(run.id)
            elif run.state == State.CLEANING:
                await runtime.runs.cleanup(run.id)
            elif run.expires <= now():
                await runtime.repo.cleaning(run.id, State.EXPIRED)
                await runtime.runs.cleanup(run.id)
        except Exception:
            logging.warning("Limpieza pendiente para corrida %s", run.id)
    ttl = {level: getattr(runtime.settings, f"ttl_corrida_{level}_min") for level in ("basico", "medio", "avanzado")}
    run_id = await runtime.repo.reserve_next(ttl)
    if run_id:
        try: await runtime.runs.provision(run_id)
        except Exception: logging.warning("Preparación no completada para corrida %s", run_id)
    try:
        async with runtime.repo.sessions() as s:
            rows = (await s.scalars(select(Ranking))).all()
        if rows: await runtime.cache.client.zadd("ranking:global", {str(r.user_id): r.points for r in rows})
        await runtime.cache.client.publish("ws:canal:ranking", "refresh")
    except Exception: pass


async def run(once=False):
    runtime = Runtime()
    try:
        # Mantener esta conexión exclusivamente para liderazgo. No hacer pool
        # check-in sin unlock. Si se pierde, detenerse antes del próximo tick.
        async with runtime.repo.engine.connect() as leader:
            if not await leader.scalar(text("SELECT pg_try_advisory_lock(2026110803)")):
                raise RuntimeError("Ya existe un worker")
            try:
                while True:
                    await leader.execute(text("SELECT 1"))
                    await tick(runtime)
                    if once: break
                    await asyncio.sleep(5)
            finally:
                await leader.execute(text("SELECT pg_advisory_unlock(2026110803)"))
    finally: await runtime.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    try: asyncio.run(run(parser.parse_args().once))
    except KeyboardInterrupt: pass
    except Exception: raise SystemExit("Worker detenido: revisa dependencias y liderazgo; no se exponen secretos")
