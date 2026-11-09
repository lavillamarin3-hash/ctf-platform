#!/usr/bin/env bash
# Primer administrador por consola, instalación nueva. Requiere Docker Compose
# y .env.fresh configurado. Ejemplo: bash scripts/crear_admin.sh
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli create-admin
