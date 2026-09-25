"""Puerto de salida para inyectar y limpiar una flag en una VM víctima."""

from __future__ import annotations

from typing import Literal, Protocol


class FlagInjectorGateway(Protocol):
    """Contrato independiente de SSH, WinRM u otro transporte."""

    async def inject(
        self,
        ip: str,
        path: str,
        value: str,
        os_type: Literal["linux", "windows"],
    ) -> None:
        """Escribe la bandera y falla de forma explícita si no puede confirmarse."""
        ...

    async def clear(
        self,
        ip: str,
        path: str,
        os_type: Literal["linux", "windows"],
    ) -> None:
        """Elimina la evidencia dinámica de la ejecución anterior."""
        ...
