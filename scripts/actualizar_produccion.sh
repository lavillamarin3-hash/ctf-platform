#!/usr/bin/env bash
# Actualiza instalación nueva; no migra/reinicia BD ni restaura snapshots.
# Requisitos: clon limpio, backup y .env.fresh. Detener worker con systemd
# antes del despliegue y reactivarlo después. Ejemplo: bash scripts/actualizar_produccion.sh
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
[[ -z "$(git status --short)" ]] || { echo 'Hay cambios locales; no se sobrescribirán.' >&2; exit 1; }
git pull --ff-only
compose=(docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml)
"${compose[@]}" config --quiet
"${compose[@]}" build api web
"${compose[@]}" run --rm --no-deps api python -m ctf.infrastructure.cli check
"${compose[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 180 api web
"${compose[@]}" ps
