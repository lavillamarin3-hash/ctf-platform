# 03. Detener escrituras y respaldar antes de limpiar

Completa [02](02_SERVIDOR_Y_ALMACENAMIENTO.md) primero. El siguiente capítulo elimina datos de forma permanente; este respaldo es la vía de recuperación. No se importará en la instalación nueva salvo que se decida volver al entorno anterior.

## 1. En LAB-CTFWEB: cerrar corridas y detener consumidores

1. Bloquea nuevos inicios desde la administración y termina las corridas activas mediante el cierre normal. Espera su limpieza de cuentas, flags y conexiones Guacamole. Borrar la BD antes de limpiar perdería el registro de esos recursos.
2. Identifica tareas que reinicien o actualicen la plataforma:

```bash
sudo systemctl list-timers --all --no-pager
sudo systemctl list-units --type=service --all --no-pager | grep -Ei 'cociber|ctf'
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Detén únicamente la automatización de la plataforma que hayas identificado. Anota su nombre y estado; no detengas servicios ajenos. Mantén el despliegue automático histórico detenido después del cambio de BD para que no vuelva a arrancar con la conexión antigua.

3. Dentro de `~/ctf-platform`, para la instalación histórica con el overlay de secretos utilizado:

```bash
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml stop api web
```

Si el despliegue activo usa otros archivos o nombre de proyecto, utiliza exactamente los mismos que lo iniciaron. Comprueba con `docker ps` que los consumidores quedaron detenidos. No uses `down -v`.

4. Si la versión nueva ya estuviera arrancada, detén también su worker y servicios:

```bash
sudo systemctl stop cociber-fresh-worker.service
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml stop api web
```

Omite este último bloque si aún no existe `.env.fresh` ni la unidad. Revisa otros procesos de trabajo independientes. Guacamole y sus datos se conservan.

## 2. En LAB-DB-POSTGRES: comprobar que no quedan escrituras

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres -c "SELECT datname, usename, client_addr, state FROM pg_stat_activity WHERE datname IN ('cociber_ctf','cociber_fresh') AND backend_type='client backend';"
```

La consulta debe devolver cero clientes antes del respaldo final. Si hay alguno, identifica y detén su aplicación. No se terminan conexiones por fuerza en esta guía. Comprueba también los consumidores Redis identificados en 02.

## 3. Crear respaldo privado en almacenamiento externo

Elige un punto de montaje externo real. El bloque solicita esa ruta, comprueba que sea un montaje distinto de `/` y `/mnt/db_data`, y crea un directorio único. No vuelca archivos de datos sobre el disco del sistema. Revisa `df -h` y el tamaño de la base antes: el bloque no predice el espacio final del dump.

Ejecuta completo en LAB-DB-POSTGRES:

```bash
sudo bash <<'BASH'
set -Eeuo pipefail
umask 077
read -rp 'Punto de montaje externo para el respaldo: ' backup_mount < /dev/tty
backup_mount=$(realpath -e -- "$backup_mount")
mountpoint -q "$backup_mount"
mountpoint -q /mnt/db_data
backup_device=$(stat -c %d "$backup_mount")
if [[ "$backup_device" == "$(stat -c %d /)" || "$backup_device" == "$(stat -c %d /mnt/db_data)" ]]; then
  echo 'El respaldo requiere otro filesystem, fuera de SO y datos.' >&2
  exit 1
fi
findmnt --mountpoint "$backup_mount"
df -h "$backup_mount"
backup_dir=$(mktemp -d "$backup_mount/cociber-antes-fresh-$(date -u +%Y%m%dT%H%M%S).XXXXXXXX")
sudo -u postgres /usr/lib/postgresql/16/bin/pg_dump -Fc -d cociber_ctf > "$backup_dir/cociber_ctf.dump"
/usr/lib/postgresql/16/bin/pg_restore --list "$backup_dir/cociber_ctf.dump" > "$backup_dir/contenido-pg.txt"
sudo -u postgres /usr/lib/postgresql/16/bin/pg_dumpall --globals-only > "$backup_dir/roles.sql"
tar -czf "$backup_dir/postgresql-config.tar.gz" -C /etc/postgresql/16 main
systemctl is-active --quiet cociber-redis.service
trap 'systemctl start cociber-redis.service' EXIT
systemctl stop cociber-redis.service
tar --numeric-owner -czf "$backup_dir/redis-datos.tar.gz" -C /mnt/db_data/redis .
tar --numeric-owner -czf "$backup_dir/redis-config.tar.gz" -C /etc/cociber-redis .
systemctl start cociber-redis.service
trap - EXIT
tar -tzf "$backup_dir/redis-datos.tar.gz" > "$backup_dir/contenido-redis.txt"
cd -- "$backup_dir"
sha256sum cociber_ctf.dump roles.sql postgresql-config.tar.gz redis-datos.tar.gz redis-config.tar.gz > SHA256SUMS
sha256sum -c SHA256SUMS
printf 'Respaldo: %s\n' "$backup_dir"
BASH
```

Guarda la ruta final. Si falla cualquier paso, detente y revisa los servicios; no continúes con el borrado. El archivo `roles.sql` y el respaldo ACL contienen hashes sensibles. No los subas al repositorio ni los compartas en capturas.

El respaldo Redis conserva **todos los índices** y el AOF multipartes completo; es necesario coordinar la breve parada con cualquier otro consumidor. No cambies su ruta ni copies únicamente un `appendonly.aof`. Si el servicio o las rutas reales no coinciden con 02, adapta primero el inventario, no ejecutes este bloque tal cual.

Listar el dump y comprobar hashes detecta algunos errores de lectura, pero no demuestra que la restauración funcione. Antes de eliminar el original, ensaya una restauración en una instancia aislada con la misma versión y comprueba sus datos. La [guía 07](07_VALIDACION_Y_RECUPERACION.md) describe qué conservar y qué verificar.

## 4. Mantener el estado de mantenimiento

PostgreSQL y Redis quedan activos para las operaciones administrativas. API, web, worker y automatizaciones antiguas permanecen detenidos. Los consumidores no deben volver a escribir entre el respaldo, la limpieza y el cambio de configuración.

Siguiente: [04. Limpieza y PostgreSQL 16](04_LIMPIEZA_Y_POSTGRESQL_16.md).
