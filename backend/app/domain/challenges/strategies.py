"""Patrón Strategy para preparar retos sin acoplar la orquestación a un escenario.

En esta fase solo se define el punto de extensión y una estrategia genérica.
Las estrategias específicas de MITRE/Atomic Red Team se incorporarán después.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChallengeStrategyContext:
    """Datos mínimos que una estrategia necesita para seleccionar recursos."""

    code: str
    scenario: str | None
    asset_references: tuple[str, ...]


@dataclass(frozen=True)
class ChallengeStrategyPlan:
    """Resultado neutral que consumirá el futuro orquestador."""

    strategy_name: str
    target_references: tuple[str, ...]


class ChallengeStrategy(Protocol):
    """Contrato de una estrategia de preparación de reto."""

    name: str

    def supports(self, context: ChallengeStrategyContext) -> bool:
        """Indica si la estrategia puede manejar el reto."""
        ...

    def prepare(self, context: ChallengeStrategyContext) -> ChallengeStrategyPlan:
        """Construye un plan sin ejecutar infraestructura todavía."""
        ...


class GenericChallengeStrategy:
    """Estrategia de respaldo para cualquier reto con referencias de activos."""

    name = "generic"

    def supports(self, context: ChallengeStrategyContext) -> bool:
        return True

    def prepare(self, context: ChallengeStrategyContext) -> ChallengeStrategyPlan:
        return ChallengeStrategyPlan(
            strategy_name=self.name,
            target_references=context.asset_references,
        )


class ChallengeStrategyRegistry:
    """Registro ordenado de estrategias; la primera compatible gana."""

    def __init__(self, strategies: list[ChallengeStrategy] | None = None) -> None:
        self._strategies = strategies or [GenericChallengeStrategy()]

    def register(self, strategy: ChallengeStrategy) -> None:
        """Añade una estrategia especializada delante del respaldo genérico."""
        self._strategies.insert(0, strategy)

    def resolve(self, context: ChallengeStrategyContext) -> ChallengeStrategy:
        """Devuelve la estrategia adecuada o genera un error explícito."""
        for strategy in self._strategies:
            if strategy.supports(context):
                return strategy
        raise LookupError(f"No existe estrategia para el reto {context.code}")
