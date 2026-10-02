"""Locks distribuidos para aislar la VM víctima durante una ejecución.

La primera versión del laboratorio trabaja con una VM Linux compartida. En lugar

de añadir otra columna al esquema, Redis serializa el acceso por IP. Más adelante
el mismo contrato puede sustituirse por un pool de ChallengeInstance + snapshot.
"""

from __future__ import annotations


class LabReservationError(RuntimeError):
    """No fue posible reservar la VM víctima para una ejecución."""


class LabReservationBusy(LabReservationError):
    """La VM tiene una reserva vigente de otra ejecución."""


class LabReservationUnavailable(LabReservationError):
    """Redis no pudo confirmar el estado de la reserva."""


def reservation_key(ip: str) -> str:
    return f"ctf:lab:reservation:{ip.strip()}"


_RELEASE_SCRIPT = """
local current = redis.call('get', KEYS[1])
if not current then
    return 1
end
if current == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


_CLEANUP_SCRIPT = """
local current = redis.call('get', KEYS[1])
if current == ARGV[1] then
    redis.call('expire', KEYS[1], ARGV[2])
    return 1
end
if not current then
    return redis.call('set', KEYS[1], ARGV[1], 'NX', 'EX', ARGV[2]) and 1 or 0
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
        raise LabReservationUnavailable("Redis no está disponible para reservar la VM") from exc
    if not acquired:
        raise LabReservationBusy("La VM víctima está siendo utilizada por otra ejecución")
    return token


async def release(redis_client, ip: str, token: str | None) -> bool:
    """Confirma que el lock propio fue liberado o ya no existe, sin tocar uno ajeno."""
    if not ip or not token:
        return False
    try:
        return bool(await redis_client.eval(_RELEASE_SCRIPT, 1, reservation_key(ip), token))
    except Exception:
        # El caller conserva el pool reservado hasta poder confirmar un reintento.
        return False


async def reserve_for_cleanup(redis_client, ip: str, run_id: int, ttl_seconds: int) -> str:
    """Protege la limpieza incluso si venció el TTL; nunca toma un lock ajeno."""
    if not ip:
        raise LabReservationError("La VM destino no tiene una IP")
    token = str(run_id)
    try:
        reserved = await redis_client.eval(
            _CLEANUP_SCRIPT, 1, reservation_key(ip), token, ttl_seconds
        )
    except Exception as exc:
        raise LabReservationUnavailable("Redis no está disponible para proteger la limpieza") from exc
    if not reserved:
        raise LabReservationBusy("La VM pertenece a otra ejecución; no se puede limpiar")
    return token
