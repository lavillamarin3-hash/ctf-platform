#!/usr/bin/env python3
"""Precomprobación SIN conexiones ni escrituras para Cociber CTF producción.

Uso: python3 scripts/verificar_entorno_produccion.py
No imprime contraseñas ni modifica .env, PostgreSQL, Redis ni Guacamole.
"""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import os
import stat
import sys

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
ERRORES = []
AVISOS = []


def leer_env():
    if not ENV.is_file():
        ERRORES.append("No existe .env; conserva tu archivo privado o crea uno a partir de .env.example.")
        return {}
    if os.name == "posix" and stat.S_IMODE(ENV.stat().st_mode) & 0o077:
        ERRORES.append("Protege .env con chmod 600 .env (no debe ser accesible para grupo/otros).")
    valores = {}
    for linea in ENV.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
            valor = valor[1:-1]
        valores[nombre.strip()] = valor
    return valores


def requiere(valores, clave):
    valor = valores.get(clave, "").strip()
    if not valor or any(item in valor.upper() for item in
                        ("CHANGE_ME", "REEMPLAZAR", "GENERAR_EN_PRIVADO", "URL_ENCODED", "CLAVE_CODIFICADA")):
        ERRORES.append(f"Falta configurar un valor privado real para {clave}.")
        return ""
    return valor


def comprobar_url(valores, clave, esquema, puerto, bd):
    dato = requiere(valores, clave)
    if not dato:
        return
    try:
        url = urlsplit(dato)
        if url.scheme != esquema or url.hostname != "10.10.10.14" or url.port != puerto:
            ERRORES.append(f"{clave} debe usar {esquema} y 10.10.10.14:{puerto}.")
        if not url.username or not url.password:
            ERRORES.append(f"{clave} requiere usuario y contraseña propios de la aplicación.")
        if url.path.lstrip("/") != bd:
            ERRORES.append(f"{clave} debe indicar la base lógica {bd}.")
        if clave == "DATABASE_URL" and parse_qs(url.query).get("ssl", [""])[0] not in ("require", "verify-full"):
            ERRORES.append("DATABASE_URL debe incluir ?ssl=require o ?ssl=verify-full según la configuración TLS.")
    except ValueError:
        ERRORES.append(f"{clave} no es una URL válida. Codifica caracteres especiales de las contraseñas.")


def main():
    valores = leer_env()
    if valores:
        comprobar_url(valores, "DATABASE_URL", "postgresql+asyncpg", 5432, "cociber_ctf")
        comprobar_url(valores, "REDIS_URL", "redis", 6379, "0")
        for clave in ("JWT_SECRET", "FIELD_HMAC_SECRET"):
            requiere(valores, clave)
        if valores.get("MANAGE_SCHEMA_ON_STARTUP", "").lower() != "false":
            ERRORES.append("MANAGE_SCHEMA_ON_STARTUP debe ser false; no alterar las tablas existentes.")
        if valores.get("CTF_SEED_DEMO_DATA", "").lower() != "false":
            ERRORES.append("CTF_SEED_DEMO_DATA debe ser false en producción.")
        if valores.get("GUACAMOLE_MODE", "").lower() == "stub":
            AVISOS.append("Guacamole está en modo stub: preserva la configuración REAL existente antes de publicar.")
        if valores.get("WEB_BIND_IP", "10.10.10.13") != "10.10.10.13":
            AVISOS.append("WEB_BIND_IP no es 10.10.10.13; comprueba que sea la IP privada de tu VM web.")
        origen = valores.get("PUBLIC_ORIGIN", "")
        if not origen.startswith(("http://", "https://")) or "localhost" in origen:
            ERRORES.append("PUBLIC_ORIGIN debe ser la dirección real del sitio, no localhost.")
    for aviso in AVISOS:
        print("AVISO:", aviso)
    if ERRORES:
        for error in ERRORES:
            print("ERROR:", error, file=sys.stderr)
        return 1
    print("Precomprobación OK: archivos y URLs coherentes. No se probaron conexiones reales.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
