"""Servicio de dominio para generar y comparar banderas dinámicas.

No conoce FastAPI, SQLAlchemy, Redis, Guacamole ni Prism. La persistencia y
la infraestructura se inyectan desde capas superiores.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable


class FlagService:
    """Genera banderas únicas y delega la verificación del hash al adaptador.

    La función ``verifier`` se inyecta para conservar la independencia del
    dominio respecto del mecanismo de hash utilizado por la plataforma.
    """

    def __init__(self, verifier: Callable[[str, str], bool] | None = None) -> None:
        self._verifier = verifier

    def generar_bandera(self, codigo_reto: str) -> str:
        """Genera una flag aleatoria con el formato definido en el diseño."""
        code = codigo_reto.strip().lower()
        if not code:
            raise ValueError("El código del reto no puede estar vacío")
        return f"FLAG{{{code}_{secrets.token_hex(16)}}}"

    def render_template(self, template: str, *, code: str, username: str, run_id: int) -> str:
        """Expande las variables públicas y usa 32 hex para la entropía por ejecución."""
        if not template.strip():
            raise ValueError("La plantilla de la flag no puede estar vacía")
        value = template
        value = value.replace("{{CODE}}", code)
        value = value.replace("{{USER}}", username)
        value = value.replace("{{RUN_ID}}", str(run_id))
        value = value.replace("{{RAND}}", secrets.token_hex(16))
        if "{{" in value or "}}" in value:
            raise ValueError("La plantilla contiene una variable no soportada")
        return value

    def validar_hash(self, valor_enviado: str, valor_hash: str) -> bool:
        """Valida una bandera usando el verificador suministrado por infraestructura."""
        if self._verifier is None:
            raise RuntimeError("FlagService requiere un verificador para validar hashes")
        if not valor_enviado or not valor_hash:
            return False
        return self._verifier(valor_enviado, valor_hash)
