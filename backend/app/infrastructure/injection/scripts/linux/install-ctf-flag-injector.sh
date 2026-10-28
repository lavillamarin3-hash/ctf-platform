#!/usr/bin/env bash
# Instalación manual de la función de inyección en la VM víctima autorizada.
# NO altera contraseñas ni la configuración de SSH y NO escribe banderas.
set -Eeuo pipefail
umask 077

[[ "$(id -u)" -eq 0 ]] || { echo "Ejecutar como root/sudo en LAB-LNXVICT" >&2; exit 1; }
[[ $# -le 1 ]] || { echo "Uso: sudo bash install-ctf-flag-injector.sh [usuario-ssh-existente]" >&2; exit 2; }
SERVICE_USER="${1:-ctf-injector}"
[[ "$SERVICE_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || { echo "Nombre de usuario no permitido" >&2; exit 2; }

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SCRIPT="$SOURCE_DIR/ctf-inject-flag.sh"
TARGET_SCRIPT="/usr/local/sbin/ctf-inject-flag.sh"
SUDOERS_FILE="/etc/sudoers.d/ctf-flag-injector-$SERVICE_USER"

[[ -f "$SOURCE_SCRIPT" && ! -L "$SOURCE_SCRIPT" ]] || { echo "El script fuente no está disponible" >&2; exit 1; }
command -v visudo >/dev/null || { echo "Falta visudo" >&2; exit 1; }
command -v bash >/dev/null && bash -n "$SOURCE_SCRIPT"

# Si el instructor especifica un usuario, debe existir previamente. No se
# cambia su clave y nunca se habilita autenticación insegura automáticamente.
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  if [[ "$#" -eq 1 ]]; then
    echo "El usuario SSH indicado no existe. No se crearán credenciales." >&2
    exit 1
  fi
  useradd --create-home --shell /bin/bash "$SERVICE_USER"
fi

# No reemplazar silenciosamente un inyector instalado que podría estar siendo
# usado por una corrida en curso; se requiere revisión durante mantenimiento.
if [[ -e "$TARGET_SCRIPT" || -L "$TARGET_SCRIPT" ]]; then
  [[ -f "$TARGET_SCRIPT" && ! -L "$TARGET_SCRIPT" ]] || { echo "Destino inválido" >&2; exit 1; }
  cmp -s "$SOURCE_SCRIPT" "$TARGET_SCRIPT" || {
    echo "El inyector instalado difiere. Programa mantenimiento y actualízalo manualmente; no se sobrescribió." >&2
    exit 1
  }
else
  install -o root -g root -m 0750 "$SOURCE_SCRIPT" "$TARGET_SCRIPT"
fi

RULE="$SERVICE_USER ALL=(root) NOPASSWD: $TARGET_SCRIPT"
if [[ -e "$SUDOERS_FILE" || -L "$SUDOERS_FILE" ]]; then
  [[ -f "$SUDOERS_FILE" && ! -L "$SUDOERS_FILE" ]] || { echo "Archivo sudoers no válido" >&2; exit 1; }
  [[ "$(cat "$SUDOERS_FILE")" == "$RULE" ]] || {
    echo "La regla sudoers existente es distinta; revisión manual necesaria." >&2; exit 1;
  }
else
  tmp="$(mktemp /etc/sudoers.d/.ctf-flag.XXXXXX)"
  trap 'rm -f -- "$tmp"' EXIT
  printf '%s\n' "$RULE" > "$tmp"
  chmod 0440 "$tmp"
  visudo -cf "$tmp" >/dev/null
  mv -- "$tmp" "$SUDOERS_FILE"
  trap - EXIT
fi
chown root:root "$TARGET_SCRIPT" "$SUDOERS_FILE"
chmod 0750 "$TARGET_SCRIPT"
chmod 0440 "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE" >/dev/null
install -d -o root -g root -m 0755 /opt/ctf
echo "Inyector y sudoers configurados para la cuenta existente: $SERVICE_USER"
echo "No se crearon flags, conexiones Guacamole ni cuentas de estudiantes."
