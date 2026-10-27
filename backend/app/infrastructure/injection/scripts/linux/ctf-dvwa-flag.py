#!/usr/bin/env python3
"""Instalar root:root, 0750; sudoers permite exclusivamente este archivo a labops.

Operaciones idempotentes por corrida: SOLO ctf_app_db.secrets, nunca dvwa.
La flag llega por stdin, no por argumentos, logs o listado de procesos.
"""
from __future__ import annotations

import re
import subprocess
import sys


def sql_command(argv: list[str], stdin: str) -> str:
    if len(argv) != 2 or argv[0] not in ("--upsert", "--delete"):
        raise ValueError("Uso: --upsert ID / --delete ID")
    raw_id = argv[1]
    if not re.fullmatch(r"[1-9][0-9]{0,9}", raw_id):
        raise ValueError("ID inválido")
    record = int(raw_id)
    if not 1_000_001 <= record <= 2_147_483_647:
        raise ValueError("La fila no pertenece a una corrida")
    if argv[0] == "--delete":
        if stdin:
            raise ValueError("La eliminación no acepta datos")
        return f"DELETE FROM ctf_app_db.secrets WHERE id={record};"
    value = stdin.removesuffix("\n")
    if not re.fullmatch(r"FLAG\{dvwa_sql_[0-9a-f]{40}\}", value):
        raise ValueError("Formato de evidencia no válido")
    return ("INSERT INTO ctf_app_db.secrets(id, flag) "
            f"VALUES ({record}, '{value}') ON DUPLICATE KEY UPDATE flag=VALUES(flag);")


def main() -> int:
    try:
        data = sys.stdin.read(130)  # Máximo 64 caracteres + nueva línea.
        sql = sql_command(sys.argv[1:], data)
        p = subprocess.run(
            ["/usr/bin/mariadb", "--batch", "--silent"],
            input=sql, text=True, capture_output=True, timeout=10, check=False,
        )
        if p.returncode:
            raise RuntimeError("Error al escribir en la base CTF")
        return 0
    except (ValueError, RuntimeError, subprocess.TimeoutExpired):
        print("La operación de evidencia no se completó", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
