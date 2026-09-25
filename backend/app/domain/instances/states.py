"""Estados válidos del ciclo de vida de una instancia de laboratorio.

El almacenamiento utiliza texto para mantener compatibilidad con PostgreSQL
existente. Las constantes evitan repetir cadenas por todo el backend.
"""

from enum import StrEnum


class InstanceState(StrEnum):
    """Estados definidos por la arquitectura de banderas dinámicas."""

    AVAILABLE = "disponible"
    RESERVING = "reservando"
    READY = "lista"
    IN_USE = "en_uso"
    REVERTING = "revirtiendo"
    ERROR = "error"
