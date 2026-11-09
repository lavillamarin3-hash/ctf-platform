#!/usr/bin/env bash
# Prueba real create/check/destroy, drena la VM primero. No imprime la flag.
# Requisitos: claves/known_hosts montados; helpers instalados; inventario cargado.
# Ejemplo: bash scripts/probar_inyector.sh LAB-LNXVICT SSH-PASSWORD-LAB
set -euo pipefail
[[ $# == 2 ]] || { echo 'Uso: probar_inyector.sh MAQUINA ESTRATEGIA' >&2; exit 2; }
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli test-injector "$1" "$2"
