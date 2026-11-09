#!/usr/bin/env python3
"""Lanza el proceso único de cola/limpieza en la imagen API nueva.

Requisitos: Docker Compose, .env.fresh y helpers configurados.
Ejemplo desde el host, con la unidad systemd detenida:
python3 scripts/cleanup_expired_runs.py --once
"""
import argparse
from pathlib import Path
import subprocess

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    command = ["docker", "compose", "--env-file", ".env.fresh", "-f", "deploy/docker-compose.fresh.yml",
               "run", "--rm", "--no-deps", "--name", "cociber-fresh-worker", "api", "python", "-m", "ctf.infrastructure.worker"]
    if args.once: command.append("--once")
    raise SystemExit(subprocess.call(command, cwd=root))
