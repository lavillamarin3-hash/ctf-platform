#!/usr/bin/env bash
# ============================================================
# PREPARACIÓN MANUAL DE LA VM VÍCTIMA
# Ejecutar una sola vez en la VM Linux del laboratorio como root.
# ============================================================
set -euo pipefail

SERVICE_USER="ctf-injector"
TARGET_SCRIPT="/usr/local/sbin/ctf-inject-flag.sh"
SUDOERS_FILE="/etc/sudoers.d/ctf-flag-injector"

install -d -m 0755 /opt/ctf

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$SERVICE_USER"
fi

install -o root -g root -m 0750 ctf-inject-flag.sh "$TARGET_SCRIPT"

cat > "$SUDOERS_FILE" <<EOF
$SERVICE_USER ALL=(root) NOPASSWD: $TARGET_SCRIPT
EOF
chmod 0440 "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE"

echo "Cuenta preparada: $SERVICE_USER"
echo "Script: $TARGET_SCRIPT"
echo "Sudoers: $SUDOERS_FILE"
