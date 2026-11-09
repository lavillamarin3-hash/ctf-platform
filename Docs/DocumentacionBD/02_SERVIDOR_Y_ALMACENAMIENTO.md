# 02. Revisar el servidor y almacenamiento existentes

Ejecutar en **LAB-DB-POSTGRES, 10.10.10.14**. La guía original registró hostname `lab-db-ctf`; el nombre visible en Nutanix puede ser LAB-DB-POSTGRES. No hace falta renombrar Linux.

El operador indica 4 cores y 32 GiB. El dato «2.72 GiB /» no permite determinar por sí solo cuánto espacio está libre en la raíz; se comprueba a continuación. Las guías anteriores describen un disco de datos de 2 TB en `/mnt/db_data`, pero su estado debe verificarse ahora.

## 1. Consultar sin cambiar nada

```bash
hostnamectl
ip -br address
cat /etc/os-release
lscpu | head -n 18
free -h
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
findmnt --mountpoint /mnt/db_data -o SOURCE,TARGET,FSTYPE,OPTIONS
df -hT / /mnt/db_data
sudo ls -ld /mnt/db_data /mnt/db_data/postgres /mnt/db_data/redis
pg_lsclusters
sudo systemctl status postgresql@16-main.service cociber-redis.service --no-pager
```

Resultados esperados del despliegue anterior: cluster PostgreSQL `16/main`, Redis bajo `cociber-redis.service`, datos en las subcarpetas indicadas. Si no coinciden, resuelve el inventario antes de continuar. No instales otro motor para hacer coincidir una salida.

## 2. Verificar PostgreSQL y acceso local

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -v ON_ERROR_STOP=1 -d postgres <<'SQL'
SELECT version();
SHOW data_directory;
SHOW hba_file;
SHOW ssl;
SELECT datname, pg_get_userbyid(datdba) AS propietario,
       pg_size_pretty(pg_database_size(oid)) AS tamano
FROM pg_database WHERE NOT datistemplate ORDER BY datname;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole
FROM pg_roles WHERE rolname IN ('cociberctf', 'cociber_app');
SELECT datname, usename, client_addr, state
FROM pg_stat_activity WHERE backend_type = 'client backend';
SQL
```

Se espera `cociberctf` administrador y `cociber_app` sin superusuario. No consultes `pg_authid` para compartir una captura: contiene hashes. Anota si `cociber_fresh` ya existe; **no se borrará automáticamente**. Si contiene tablas, esta secuencia no debe inicializarla encima.

## 3. Verificar Redis

```bash
sudo systemctl show cociber-redis.service -p ExecStart -p ReadWritePaths
/opt/cociber-redis/current/bin/redis-server --version
sudo ss -ltnp '( sport = :5432 or sport = :6379 )'
```

La guía original fijaba Redis 7.4.11. Aquí se conserva el binario existente y se comprueba que sea 7.x; no se descarga ni recompila. Para consultar datos, abre una sesión Bash normal y escribe la contraseña administrativa de Redis al solicitarla:

```bash
read -rsp 'Contraseña Redis de cociberctf: ' REDISCLI_AUTH; printf '\n'
export REDISCLI_AUTH
redis_admin() { /opt/cociber-redis/current/bin/redis-cli --user cociberctf -h 127.0.0.1 "$@"; }
redis_admin PING
redis_admin INFO keyspace
redis_admin CLIENT LIST
redis_admin CONFIG GET dir dbfilename appendonly appenddirname aclfile databases
unset REDISCLI_AUTH
unset -f redis_admin
```

No se imprime la contraseña. `INFO keyspace` muestra únicamente índices no vacíos; no demuestra qué aplicación es dueña de cada uno. Confirma el índice en el `REDIS_URL` privado de cada consumidor. Las bases lógicas de Redis comparten usuarios y canales Pub/Sub; `/1` organiza claves, no constituye una frontera de permisos.

## 4. Condiciones para continuar

- `/mnt/db_data` debe ser un montaje real y los motores deben apuntar a él.
- Deben estar identificados todos los consumidores de `cociber_ctf` y Redis `/0`.
- Debe existir un destino de respaldo con capacidad suficiente, distinto del disco de datos y de la raíz.
- La aplicación nueva seguirá entrando desde 10.10.10.13 hacia 5432 y 6379; no se abre acceso a VLAN20/30.

No ejecutes `mkfs`, `pg_dropcluster`, cambios de particiones ni borrados de `/mnt/db_data`. La limpieza solicitada es lógica y no requiere cambiar montajes, UUID, propietarios de todo el disco o memoria de los motores.

Siguiente: [03. Mantenimiento y respaldo](03_MANTENIMIENTO_Y_RESPALDO.md).
