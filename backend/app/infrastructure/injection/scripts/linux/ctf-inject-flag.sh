#!/usr/bin/env bash
# ============================================================
# INYECTOR DE FLAGS DEL LABORATORIO CTF
# Ejecutar solo mediante sudoers y desde la cuenta de servicio.
# ============================================================
set -euo pipefail

FLAG_PATH=""
FLAG_VALUE=""
CLEAR_FLAG="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      FLAG_PATH="${2:-}"
      shift 2
      ;;
    --flag)
      FLAG_VALUE="${2:-}"
      shift 2
      ;;
    --clear)
      CLEAR_FLAG="true"
      shift
      ;;
    *)
      echo "Argumento no permitido" >&2
      exit 2
      ;;
  esac
done

# La cuenta de servicio nunca debe poder escribir fuera del árbol CTF.
case "$FLAG_PATH" in
  /opt/ctf/*) ;;
  *) echo "Ruta no permitida" >&2; exit 3 ;;
esac

if [[ "$CLEAR_FLAG" == "true" ]]; then
  rm -f -- "$FLAG_PATH"
  [[ ! -e "$FLAG_PATH" ]] || { echo "No se pudo limpiar la bandera" >&2; exit 7; }
  printf '%s\n' "CLEARED"
  exit 0
fi

if [[ -z "$FLAG_VALUE" ]]; then
  echo "La bandera no puede estar vacía" >&2
  exit 4
fi

install -d -m 0755 "$(dirname "$FLAG_PATH")"
tmp_file="$(mktemp "$(dirname "$FLAG_PATH")/.flag.XXXXXX")"
printf '%s\n' "$FLAG_VALUE" > "$tmp_file"
chmod 0644 "$tmp_file"
mv -f "$tmp_file" "$FLAG_PATH"

# Verificación mínima: confirmar que el archivo existe y contiene una sola línea.
[[ -s "$FLAG_PATH" ]] || { echo "No se pudo confirmar la escritura" >&2; exit 5; }
[[ "$(wc -l < "$FLAG_PATH")" -ge 1 ]] || { echo "Contenido inválido" >&2; exit 6; }

printf '%s\n' "OK"
