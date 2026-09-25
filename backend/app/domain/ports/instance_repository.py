"""Puerto de persistencia para el pool de instancias.

El dominio depende de este contrato, no de SQLAlchemy.
"""

from __future__ import annotations

from typing import Protocol

from ..instances.states import InstanceState


class InstanceRepositoryPort(Protocol):
    """Operaciones mínimas requeridas por la futura orquestación."""

    async def find_available(self, challenge_id: int):
        """Obtiene una instancia disponible de forma compatible con locks."""
        ...

    async def get(self, instance_id: int):
        """Obtiene una instancia por identificador."""
        ...

    async def set_state(self, instance_id: int, state: InstanceState, **fields):
        """Actualiza el estado y metadatos operativos de una instancia."""
        ...
