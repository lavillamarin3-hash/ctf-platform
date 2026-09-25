"""Locks distribuidos para aislar la VM víctima durante una ejecución.

La primera versión del laboratorio trabaja con una VM Linux compartida. En lugar

de añadir otra columna al esquema, Redis serializa el acceso por IP. Más adelante
el mismo contrato puede sustituirse por un pool de ChallengeInstance + snapshot.
"""

from __future__ import annotations


class LabReservationError(RuntimeError):
    """No fue posible reservar la VM víctima para una ejecución."""


def reservation_key(ip: str) -> str:
    return f"ctf:lab:reservation:{ip.strip()}"


_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


async def acquire(redis_client, ip: str, run_id: int, ttl_seconds: int) -> str:
    """Reserva la IP con un token único y TTL para evitar colisiones de ejecuciones."""
    if not ip:
        raise LabReservationError("La VM destino no tiene una IP")
    token = str(run_id)
    key = reservation_key(ip)
    try:
        acquired = await redis_client.set(key, token, nx=True, ex=ttl_seconds)
    except Exception as exc:  # pragma: no cover - depende de infraestructura
        raise LabReservationError("Redis no está disponible para reservar la VM") from exc
    if not acquired:
        raise LabReservationError("La VM víctima está siendo utilizada por otra ejecución")
    return token


async def release(redis_client, ip: str, token: str | None) -> None:
    """Libera solo el lock que pertenece al caller actual."""
    if not ip or not token:
        return
    try:
        await redis_client.eval(_RELEASE_SCRIPT, 1, reservation_key(ip), token)
    except Exception:
        # El TTL garantiza recuperación eventual aunque Redis falle durante el cierre.
        return
