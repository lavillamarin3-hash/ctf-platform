#!/usr/bin/env bash
# CoCiber CTF · despliegue supervisado de main (instalado como copia root-owned).
# No crea usuarios/VMs/conexiones Guacamole ni toca PostgreSQL/Redis.
set -Eeuo pipefail
umask 077

MODE="${1:---once}"
case "$MODE" in --once|--dry-run) ;; *) echo "Uso: $0 [--once|--dry-run]" >&2; exit 2 ;; esac
APP_DIR="${APP_DIR:?APP_DIR debe definirse en /etc/cociber-ctf/auto-deploy.conf}"
APP_USER="${APP_USER:?APP_USER debe definirse en /etc/cociber-ctf/auto-deploy.conf}"
GH_REPO="${GH_REPO:-lavillamarin3-hash/ctf-platform}"
HEALTH_URL="${HEALTH_URL:-http://10.10.10.13:8081/api/v1/health}"
CI_WORKFLOW="ctf-quality.yml"

log() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }
die() { log "ERROR: $*"; exit 1; }
[[ "$APP_DIR" = /* && -d "$APP_DIR/.git" ]] || die "APP_DIR no apunta al clon Git del proyecto"
[[ -f "$APP_DIR/docker-compose.prod.yml" && -f "$APP_DIR/.env" ]] || die "Falta compose de producción o .env local"
[[ "$GH_REPO" == "lavillamarin3-hash/ctf-platform" ]] || die "Repositorio no autorizado"
[[ "$HEALTH_URL" == "http://10.10.10.13:8081/api/v1/health" ]] || die "Health URL fuera del servidor de aplicación esperado"
command -v flock >/dev/null && command -v runuser >/dev/null || die "Faltan flock o runuser"
command -v git >/dev/null && command -v docker >/dev/null || die "Faltan git o docker"
command -v curl >/dev/null && command -v python3 >/dev/null || die "Faltan curl o python3"

# Evita dos despliegues simultáneos.
exec 9>/run/lock/cociber-ctf-auto-deploy.lock
flock -n 9 || { log "Otro despliegue está ejecutándose. Se omite esta revisión."; exit 0; }

git_app() { runuser -u "$APP_USER" -- git -C "$APP_DIR" "$@"; }
compose() { (cd "$APP_DIR" && docker compose -f docker-compose.prod.yml "$@"); }

[[ "$(git_app branch --show-current)" == main ]] || die "El clon no está en main"
[[ -z "$(git_app status --porcelain --untracked-files=normal)" ]] || die "Existen cambios locales; no se sobrescribirán"
case "$(git_app remote get-url origin)" in
  "https://github.com/lavillamarin3-hash/ctf-platform.git"|"https://github.com/lavillamarin3-hash/ctf-platform"|"git@github.com:lavillamarin3-hash/ctf-platform.git"|"git@github.com:lavillamarin3-hash/ctf-platform") ;;
  *) die "origin no es el repositorio esperado" ;;
esac

# Descarga únicamente la referencia de main. No cambia archivos todavía.
git_app fetch --no-tags origin '+refs/heads/main:refs/remotes/origin/main'
OLD_SHA="$(git_app rev-parse HEAD)"
NEW_SHA="$(git_app rev-parse refs/remotes/origin/main)"
if [[ "$NEW_SHA" == "$OLD_SHA" ]]; then
  log "Sin cambios; main=$OLD_SHA"
  exit 0
fi
git_app merge-base --is-ancestor "$OLD_SHA" "$NEW_SHA" || die "main remoto no es fast-forward; revisar manualmente"

# Solo se despliega el SHA exacto si la ejecución push de CI aprobó.
check_ci() {
  local url json result
  url="https://api.github.com/repos/$GH_REPO/actions/workflows/$CI_WORKFLOW/runs?branch=main&event=push&head_sha=$NEW_SHA&per_page=15"
  local -a headers=(-H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2022-11-28')
  # Este repositorio es público; no necesita token. Si cambia a privado,
  # configurar DEPLOY_GITHUB_TOKEN solo en /etc/cociber-ctf/auto-deploy.conf (0600).
  if [[ -n "${DEPLOY_GITHUB_TOKEN:-}" ]]; then
    headers+=(-H "Authorization: Bearer ${DEPLOY_GITHUB_TOKEN}")
  fi
  json="$(curl --fail --silent --show-error --max-time 20 --retry 2 "${headers[@]}" "$url")" || return 2
  result="$(printf '%s' "$json" | python3 -c '
import json, sys
try:
    d=json.load(sys.stdin)
    sha=sys.argv[1]
    runs=[r for r in d.get("workflow_runs",[]) if
          r.get("head_sha")==sha and r.get("event")=="push" and r.get("head_branch")=="main"]
    runs.sort(key=lambda r: (str(r.get("created_at","")),int(r.get("run_attempt") or 0)),reverse=True)
    if not runs: print("pending")
    elif runs[0].get("status")!="completed": print("pending")
    elif runs[0].get("conclusion")=="success": print("success")
    else: print("failure")
except (ValueError,TypeError,AttributeError,KeyError):
    sys.exit(2)
' "$NEW_SHA")" || return 2
  [[ "$result" == success ]] && return 0
  [[ "$result" == pending || "$result" == failure ]] && { log "CI para $NEW_SHA: $result. NO se despliega."; return 1; }
  return 2
}
log "Nuevo commit detectado: $OLD_SHA → $NEW_SHA"
if ! check_ci; then
  log "El cambio queda pendiente. Se volverá a revisar en el siguiente ciclo."
  exit 0
fi

if [[ "$MODE" == --dry-run ]]; then
  log "Simulación OK: $NEW_SHA tiene CI aprobado. No se modificó el servidor."
  exit 0
fi

health_ok() {
  local response
  response="$(curl --silent --show-error --fail --max-time 5 "$HEALTH_URL")" || return 1
  printf '%s' "$response" | python3 -c '
import json,sys
try:
    v=json.load(sys.stdin)
    sys.exit(0 if v.get("status")=="ok" and v.get("service")=="ctf-api" else 1)
except (ValueError,AttributeError): sys.exit(1)
'
}
wait_health() {
  local n
  for n in $(seq 1 24); do
    if health_ok; then return 0; fi
    sleep 3
  done
  return 1
}

# Se exige un despliegue operativo ANTES de cambiar el código.
health_ok || die "La API actual no pasa /health; intervención manual antes de desplegar"
compose config --quiet || die "Compose actual inválido"
log "Actualizando main y reconstruyendo exclusivamente api/web"
git_app merge --ff-only "$NEW_SHA" || die "No fue posible avanzar main"

deploy_ok=false
if compose config --quiet && compose build api web && compose up -d --no-deps api web && wait_health; then
  deploy_ok=true
fi
if [[ "$deploy_ok" != true ]]; then
  log "ERROR: el nuevo despliegue falló. Restaurando código $OLD_SHA y contenedores previos..."
  # Seguro porque exigimos un árbol limpio y solo avanzamos por fast-forward.
  git_app reset --hard "$OLD_SHA" || die "Fallo crítico: restauración del árbol Git no completada"
  if compose config --quiet && compose build api web && compose up -d --no-deps api web && wait_health; then
    log "Rollback completado; versión anterior restaurada. Revisar logs del servicio."
  else
    die "Rollback NO confirmado: requiere intervención urgente."
  fi
  exit 1
fi

log "Despliegue confirmado: $NEW_SHA. Guacamole permanece en su VM independiente."
# Solo lectura; un fallo temporal de Guacamole NO debe destruir un despliegue sano.
if ! compose exec -T api python - <<'PY'
import asyncio
from app.core import get_settings
from app.guacamole import make_guacamole_admin

async def main():
    if get_settings().guacamole_mode.lower() != "real":
        raise SystemExit("ADVERTENCIA: Guacamole está en modo stub, no se puede verificar inventario")
    try:
        connections = await make_guacamole_admin().list_connections()
    except Exception:
        raise SystemExit("No fue posible consultar conexiones en Guacamole")
    print(f"Guacamole remoto: {len(connections)} conexiones consultadas (sin modificarlas).")

asyncio.run(main())
PY
then
  log "AVISO: inventario Guacamole no verificado. Revisar URL API, credenciales y conexión entre VMs; NO recrear conexiones."
fi
log "Finalizado. El certificado TLS del proxy externo requiere gestión independiente."
