# 05. Limpiar Redis del CTF y preparar sus permisos

Ejecutar en **LAB-DB-POSTGRES**, con API y worker detenidos y respaldo completo de [03](03_MANTENIMIENTO_Y_RESPALDO.md). Se conservan Redis, su configuración y las contraseñas. No borrar `/mnt/db_data/redis`, RDB, AOF ni `users.acl`.

## 1. Autenticarse como administrador sin contraseña en argumentos

En la misma sesión Bash donde ejecutarás este capítulo:

```bash
read -rsp 'Contraseña Redis de cociberctf: ' REDISCLI_AUTH; printf '\n'
export REDISCLI_AUTH
redis_admin() { /opt/cociber-redis/current/bin/redis-cli --user cociberctf -h 127.0.0.1 "$@"; }
redis_admin PING
redis_admin ACL WHOAMI
redis_admin ACL USERS
redis_admin INFO keyspace
redis_admin -n 0 DBSIZE
redis_admin -n 1 DBSIZE
```

Esperado: PONG, usuario `cociberctf`, presencia de `cociber_app`. Si falta la cuenta de aplicación, detente y reconcilia las ACL existentes; no vuelvas a ejecutar el instalador antiguo para regenerarlas todas. Cada respuesta de Redis debe revisarse: algunos errores del servidor pueden imprimirse sin que un shell detecte un fallo.

## 2. Confirmar qué índice se va a vaciar

El generador de la guía antigua escribía `REDIS_URL=.../0`; la versión nueva usa `/1`. Verifica el índice en el archivo privado **activo** de la aplicación anterior, y que no lo use otro sistema. No compartas la URL completa.

- Si `/0` pertenece exclusivamente al CTF anterior, el siguiente bloque puede vaciarlo.
- Si es compartido o el destino real no está confirmado, **no ejecutes FLUSHDB**. Haz inventario de prefijos y consumidores antes de acordar una limpieza selectiva. No basta con que las claves parezcan del laboratorio.
- `/1` debe estar vacío para esta instalación. Si no lo está, no lo vacíes automáticamente: identifica sus datos o elige otro índice vacío y actualiza coherentemente `REDIS_URL`.

## 3. Vaciar únicamente el índice histórico confirmado

Esta acción elimina sesiones, tokens, límites de intentos y caché del índice `/0`. Se ejecuta con todos sus consumidores detenidos:

```bash
read -rp 'Con /0 confirmado exclusivo del CTF y respaldado, escribe VACIAR-CTF-REDIS-0: ' confirmed_redis
if [[ "$confirmed_redis" == 'VACIAR-CTF-REDIS-0' ]]; then
  redis_admin -n 0 FLUSHDB SYNC
  redis_admin -n 0 DBSIZE
else
  printf 'Sin cambios.\n'
fi
unset confirmed_redis
redis_admin -n 1 DBSIZE
```

Esperado tras la limpieza: `OK` y conteo 0 para `/0`; `/1` también debe estar vacío antes del arranque nuevo. **No usar FLUSHALL**: eliminaría claves de todos los índices. `FLUSHDB` actúa sobre el índice seleccionado y no elimina usuarios ACL. [Referencia oficial](https://redis.io/docs/latest/commands/flushdb/).

La reducción del archivo AOF en disco no es inmediata; no lo borres para «liberar espacio». Una reescritura de persistencia requiere margen de RAM/disco y una ventana propia. La limpieza lógica ya queda reflejada en el flujo AOF si está habilitado y sano.

## 4. Corregir el canal del ranking conservando las credenciales

La ACL antigua autoriza canales `&ctf:*`. El código nuevo publica y se suscribe a **`ws:canal:ranking`**; sin ese permiso, PONG funciona pero las notificaciones del ranking fallan.

Primero verifica el destino configurado:

```bash
redis_admin CONFIG GET aclfile
```

Si devuelve `/etc/cociber-redis/users.acl`, respalda y edita:

```bash
sudo cp -a /etc/cociber-redis/users.acl "/etc/cociber-redis/users.acl.antes-fresh.$(date -u +%Y%m%dT%H%M%S).bak"
sudoedit /etc/cociber-redis/users.acl
```

En la línea **`user cociber_app`**, conserva exactamente el hash de contraseña `#...`, estado `on`, patrones de claves y permisos existentes. Agrega únicamente este token al final de esa misma línea:

```text
&ws:canal:ranking
```

No lo pongas como una línea independiente. No cambies `user cociberctf`, no reemplaces el hash por una contraseña literal, ni pegues el archivo en capturas. Si ya existe ese permiso o `&*`, no hace falta duplicarlo. El archivo previo proporciona `~*` y las operaciones de lectura/escritura, conexiones, scripting y Pub/Sub; compruébalas mediante DRYRUN en el siguiente paso. Las ACL se procesan como reglas y los patrones `&` controlan canales. [Referencia de ACL SETUSER](https://redis.io/docs/latest/commands/acl-setuser/).

```bash
sudo chown root:redis /etc/cociber-redis/users.acl
sudo chmod 0640 /etc/cociber-redis/users.acl
redis_admin ACL LOAD
```

Debe responder `OK`. Si falla, restaura **ese archivo concreto** desde la copia recién creada, repite `ACL LOAD` y corrige el formato antes de continuar. No uses `ACL SAVE`: en el despliegue original el servicio no puede escribir en `/etc`; la persistencia se hace editando el archivo como root.

## 5. Verificar permisos sin ejecutar borrados con la cuenta de aplicación

Con la cuenta administrativa todavía autenticada:

```bash
redis_admin ACL DRYRUN cociber_app SELECT 1
redis_admin ACL DRYRUN cociber_app SET terminal:probe 1 EX 60
redis_admin ACL DRYRUN cociber_app GETDEL terminal:probe
redis_admin ACL DRYRUN cociber_app EVAL 'return 1' 0
redis_admin ACL DRYRUN cociber_app INCR rate:login:probe
redis_admin ACL DRYRUN cociber_app EXPIRE rate:login:probe 60
redis_admin ACL DRYRUN cociber_app DEL terminal:probe
redis_admin ACL DRYRUN cociber_app EXISTS jwt:revocado:probe
redis_admin ACL DRYRUN cociber_app ZADD ranking:global 0 probe
redis_admin ACL DRYRUN cociber_app PUBLISH ws:canal:ranking refresh
redis_admin ACL DRYRUN cociber_app SUBSCRIBE ws:canal:ranking
redis_admin ACL DRYRUN cociber_app CONFIG GET dir
redis_admin ACL DRYRUN cociber_app ACL USERS
redis_admin ACL DRYRUN cociber_app FLUSHDB
redis_admin ACL DRYRUN cociber_app FLUSHALL
```

Esperado: `OK` para las once operaciones funcionales; denegación para las últimas cuatro administrativas. DRYRUN **no ejecuta** el comando indicado. Si faltan permisos funcionales, corrige la regla concreta; no concedas `+@all` a `cociber_app`.

```bash
redis_admin INFO persistence
unset REDISCLI_AUTH
unset -f redis_admin
```

Conservar `aof_last_write_status:ok`, sin errores de persistencia. Las ACL no limitan al usuario por índice lógico: `SELECT 1` organiza el uso, pero no aísla datos de otras aplicaciones. No se amplía la exposición de red: 6379 sigue permitido solo desde la aplicación y administración local.

Siguiente: [06. Continuar instalación](06_CONTINUAR_INSTALACION.md).
