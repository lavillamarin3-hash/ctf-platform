#!/usr/bin/env bash
# Instalar UNA SOLA VEZ en la VM de aplicación CoCiber 10.10.10.13.
# NO instala ni toca Guacamole, PostgreSQL, Redis ni el proxy TLS.
set -Eeuo pipefail
umask 077
if (( EUID != 0 )); then echo "Ejecuta: sudo bash scripts/instalar_auto_deploy_main.sh \"\$PWD\"" >&2; exit 1; fi
if [[ "$#" -ne 1 ]]; then echo "Uso: sudo bash scripts/instalar_auto_deploy_main.sh /ruta/al/proyecto" >&2; exit 2; fi
APP_DIR="$(realpath -e "$1")"
# Ruta controlada para EnvironmentFile de systemd (sin expansión shell).
[[ "$APP_DIR" =~ ^/[[:alnum:]_./-]+$ ]] || { echo "Ruta inválida: no usar espacios ni caracteres especiales" >&2; exit 1; }
[[ -d "$APP_DIR/.git" && -f "$APP_DIR/.env" && -f "$APP_DIR/docker-compose.prod.yml" ]] || { echo "Falta .git/.env/compose.prod.yml en $APP_DIR" >&2; exit 1; }
[[ -f "$APP_DIR/scripts/cociber_auto_deploy_main.sh" ]] || { echo "No existe el script de despliegue" >&2; exit 1; }
[[ -f "$APP_DIR/deploy/systemd/cociber-ctf-auto-deploy.service" && -f "$APP_DIR/deploy/systemd/cociber-ctf-auto-deploy.timer" ]] || { echo "Faltan unidades systemd" >&2; exit 1; }
APP_USER="$(stat -c '%U' "$APP_DIR")"
id "$APP_USER" >/dev/null || { echo "El propietario del proyecto no es un usuario válido" >&2; exit 1; }
command -v docker >/dev/null && command -v git >/dev/null && command -v systemctl >/dev/null || { echo "Falta docker/git/systemd" >&2; exit 1; }
runuser -u "$APP_USER" -- git -C "$APP_DIR" rev-parse --is-inside-work-tree | grep -q true || { echo "Usuario de proyecto sin acceso Git" >&2; exit 1; }

install -d -m 0700 -o root -g root /etc/cociber-ctf
install -m 0750 -o root -g root "$APP_DIR/scripts/cociber_auto_deploy_main.sh" /usr/local/sbin/cociber-auto-deploy-main
install -m 0644 -o root -g root "$APP_DIR/deploy/systemd/cociber-ctf-auto-deploy.service" /etc/systemd/system/cociber-ctf-auto-deploy.service
install -m 0644 -o root -g root "$APP_DIR/deploy/systemd/cociber-ctf-auto-deploy.timer" /etc/systemd/system/cociber-ctf-auto-deploy.timer

# Nunca reemplazar la configuración root-owned durante futuras reinstalaciones.
if [[ ! -e /etc/cociber-ctf/auto-deploy.conf ]]; then
  {
    printf 'APP_DIR=%s\n' "$APP_DIR"
    printf 'APP_USER=%s\n' "$APP_USER"
    printf 'GH_REPO=lavillamarin3-hash/ctf-platform\n'
    printf 'HEALTH_URL=http://10.10.10.13:8081/api/v1/health\n'
  } > /etc/cociber-ctf/auto-deploy.conf
fi
chown root:root /etc/cociber-ctf/auto-deploy.conf
chmod 0600 /etc/cociber-ctf/auto-deploy.conf
systemctl daemon-reload
systemctl enable --now cociber-ctf-auto-deploy.timer
echo "Instalación activada. La primera comprobación ocurre tras OnBootSec/OnUnitActiveSec."
echo "Estado: sudo systemctl list-timers cociber-ctf-auto-deploy.timer"
echo "Prueba manual: sudo systemctl start cociber-ctf-auto-deploy.service"
echo "Logs: sudo journalctl -u cociber-ctf-auto-deploy.service -n 70 --no-pager"
echo "Pausa: sudo systemctl disable --now cociber-ctf-auto-deploy.timer"
echo "NO se alteró .env ni se recrearon conexiones de Guacamole."
