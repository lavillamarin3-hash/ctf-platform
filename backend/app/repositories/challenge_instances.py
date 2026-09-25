"""Repositorio SQLAlchemy para el pool de instancias de retos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.instances.states import InstanceState
from ..models import ChallengeInstance


class ChallengeInstanceRepository:
    """Aísla las consultas de instancias para la futura capa de aplicación."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_available(self, challenge_id: int) -> ChallengeInstance | None:
        """Reserva lógicamente la siguiente instancia libre dentro de la transacción."""
        result = await self.session.execute(
            select(ChallengeInstance)
            .where(
                ChallengeInstance.challenge_id == challenge_id,
                ChallengeInstance.state == InstanceState.AVAILABLE.value,
            )
            .order_by(ChallengeInstance.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get(self, instance_id: int) -> ChallengeInstance | None:
        """Obtiene una instancia por ID."""
        return await self.session.get(ChallengeInstance, instance_id)

    async def set_state(self, instance_id: int, state: InstanceState, **fields):
        """Actualiza estado y campos permitidos sin duplicar SQL en los casos de uso."""
        instance = await self.session.get(ChallengeInstance, instance_id)
        if instance is None:
            return None
        instance.state = state.value
        for key, value in fields.items():
            if not hasattr(instance, key):
                raise ValueError(f"Campo de instancia no permitido: {key}")
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def list_by_challenge(self, challenge_id: int) -> list[ChallengeInstance]:
        """Lista el pool completo de un reto para administración y diagnóstico."""
        result = await self.session.scalars(
            select(ChallengeInstance)
            .where(ChallengeInstance.challenge_id == challenge_id)
            .order_by(ChallengeInstance.id)
        )
        return list(result.all())
