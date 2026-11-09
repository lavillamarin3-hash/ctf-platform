#!/usr/bin/env bash
# Backup de PostgreSQL externo, formato custom, rotación de 7 días.
# Requisitos: pg_dump/pg_restore de versión compatible, PGSERVICE y PGPASSFILE
# privados (0600). No leer .env con source ni pasar claves en argumentos.
# Ejemplo: PGSERVICE=cociber PGPASSFILE=$HOME/.pgpass BACKUP_DIR=/srv/backups/cociber bash scripts/backup_db.sh
set -euo pipefail
umask 077
: "${PGSERVICE:?Configura PGSERVICE en ~/.pg_service.conf}"
: "${PGPASSFILE:?Configura un archivo pgpass privado}"
: "${BACKUP_DIR:?Indica un directorio exclusivo de backups}"
[[ "$BACKUP_DIR" = /* && "$BACKUP_DIR" != / ]] || exit 2
mkdir -p -- "$BACKUP_DIR"
file="$BACKUP_DIR/cociber-$(date -u +%Y%m%dT%H%M%SZ).dump"
temporary="$file.partial"
trap 'rm -f -- "$temporary"' EXIT
pg_dump --no-password --format=custom --file="$temporary"
pg_restore --list "$temporary" >/dev/null
mv -- "$temporary" "$file"
# Solo archivos propios del patrón, nunca subdirectorios ni enlaces.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'cociber-*.dump' -mtime +6 -delete
printf 'Backup validado: %s\n' "$file"
