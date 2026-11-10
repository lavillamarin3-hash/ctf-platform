# 07. Validar y recuperar si fuera necesario

> **Secuencia condicionada de BD.** La plataforma actual ya conecta correctamente: no repitas limpieza ni inicialización para preparar los laboratorios. Usa esta carpeta solamente para un reinicio deliberado de datos con respaldo, siguiendo su [paso 01](01_CREDENCIALES_Y_PREPARACION.md). Para continuar la instalación operativa vuelve al [índice principal](../00_Inicio/01_LEEME_PRIMERO.md).
>
> Antes de ejecutar comandos, abre la sesión del servidor indicado en cada sección mediante [acceso SSH y comandos base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). En LAB-CTFWEB ejecuta `cd /ctf-plataform/ || exit 1`; en LAB-DB-POSTGRES no se necesita esa carpeta. Si una sección cambia de servidor, abre otra terminal SSH y verifica `hostname`.

Esta lista distingue resultados esperados de resultados observados. Los comandos aún deben ejecutarse en las VM; la revisión local de esta documentación no acredita una instalación remota correcta.

## 1. Comprobar PostgreSQL desde LAB-CTFWEB

Si está disponible el cliente PostgreSQL 16, ejecuta desde 10.10.10.13:

```bash
psql 'host=10.10.10.14 port=5432 dbname=cociber_fresh user=cociber_app sslmode=require' -W -X -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_user, current_database();
SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user;
SELECT has_schema_privilege(current_user, 'public', 'CREATE') AS puede_crear_tablas;
SELECT rol_id, rol_nombre FROM "ROLES" ORDER BY rol_id;
BEGIN;
INSERT INTO "GRUPOS" (gru_codigo, gru_nombre) VALUES ('DB-VALIDACION', 'Prueba transaccional de permisos');
UPDATE "GRUPOS" SET gru_nombre='Prueba actualizada' WHERE gru_codigo='DB-VALIDACION';
SELECT gru_codigo FROM "GRUPOS" WHERE gru_codigo='DB-VALIDACION';
DELETE FROM "GRUPOS" WHERE gru_codigo='DB-VALIDACION';
ROLLBACK;
SQL
```

Esperado: cuenta `cociber_app`, base `cociber_fresh`, TLS `t`, privilegios administrativos y CREATE `f`, cuatro roles y operaciones de tabla correctas. La prueba queda revertida. Si aparece falta de permisos, corrige las concesiones de 04; no conviertas la API en superusuario.

Si no tienes `psql` en LAB-CTFWEB, el `cli check` de 06 comprueba acceso a una tabla y PING, pero no sustituye esta prueba de permisos y TLS. Puedes usar un cliente autorizado desde esa misma IP sin instalar otro servidor PostgreSQL.

## 2. Comprobar Redis desde la imagen API nueva

Desde `/ctf-plataform` en LAB-CTFWEB. Se crean solo claves temporales con identificador aleatorio y TTL; no se borra un índice:

```bash
cd /ctf-plataform/ || exit 1
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps -T api python - <<'PY'
import os, sys, uuid
from redis import Redis

client = Redis.from_url(os.environ['REDIS_URL'], decode_responses=True,
                        socket_connect_timeout=3, socket_timeout=5)
key = 'terminal:probe:' + uuid.uuid4().hex
try:
    assert client.ping()
    client.set(key, 'ok', ex=60)
    assert client.getdel(key) == 'ok'
    assert client.eval("local n=redis.call('incr',KEYS[1]); redis.call('expire',KEYS[1],60); return n", 1, key) == 1
    with client.pubsub() as subscription:
        subscription.subscribe('ws:canal:ranking')
        ack = subscription.get_message(timeout=3)
        assert ack and ack['type'] == 'subscribe'
        client.publish('ws:canal:ranking', 'refresh')
        event = subscription.get_message(ignore_subscribe_messages=True, timeout=3)
        assert event and event['data'] == 'refresh'
    print('Redis: autenticación, claves, Lua y ranking OK')
except Exception as error:
    print('Prueba Redis fallida:', type(error).__name__)
    sys.exit(1)
finally:
    try:
        client.delete(key)
    except Exception:
        pass
    client.close()
PY
```

Esta prueba valida el canal nuevo y el scripting que usa la aplicación. Una respuesta PONG aislada no basta para aceptarlos.

## 3. Comprobar el servicio y la aplicación

En LAB-DB-POSTGRES:

```bash
sudo systemctl is-active postgresql@16-main.service cociber-redis.service
df -h / /mnt/db_data
free -h
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres -c "SELECT datname FROM pg_database WHERE datname IN ('cociber_ctf','cociber_fresh');"
```

En LAB-CTFWEB:

```bash
cd /ctf-plataform/ || exit 1
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli check
```

Comprueba login y cambio de contraseña, creación de grupo/jugador, catálogo en borrador y ranking. El worker requiere configuración y supervisión aparte; que API/web estén sanos no demuestra que el worker esté activo. ESC-01/04/05 siguen deshabilitados. Las pruebas de las víctimas y consola se realizan mediante las guías de helpers y demo, no como parte de la limpieza de BD.

## 4. Diagnóstico frecuente

| Resultado | Comprobación concreta |
| --- | --- |
| PostgreSQL rechaza HBA | Regla `hostssl cociber_fresh cociber_app 10.10.10.13/32` antes del rechazo y `?ssl=require` en DATABASE_URL |
| PostgreSQL falla autenticación | Contraseña de **aplicación**, cuenta existente con LOGIN, URL codificada; no sustituir por la clave administrativa |
| «relation USUARIOS does not exist» | Base correcta y SQL de este checkout cargado; no esquema anterior |
| «permission denied» en tablas | GRANT de 04 aplicado después de cargar el esquema bajo `cociberctf` |
| Redis WRONGPASS | Usuario ACL activo y contraseña de aplicación conservada |
| Redis NOPERM en ranking | Permiso `&ws:canal:ranking` guardado en archivo y `ACL LOAD` correcto |
| `init-db` rechaza tablas existentes | Es esperado después de 04; no repetir inicialización |
| No carga la web pública | Revisar proxy TLS y DNAT; es independiente de que las bases respondan |

## 5. Ensayo de restauración previo al borrado

En una **instancia PostgreSQL 16 aislada de producción**, con el dump copiado de forma privada, puedes ensayar la estructura y los datos sin importar permisos globales:

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/createdb cociber_restore_test
```

En Bash, indicando la ruta real al dump:

```bash
set -o pipefail
sudo cat /RUTA_PRIVADA/cociber_ctf.dump | sudo -u postgres /usr/lib/postgresql/16/bin/pg_restore --exit-on-error --no-owner --no-privileges -d cociber_restore_test
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d cociber_restore_test -c '\dt'
```

No ejecutes este bloque en una base existente ni uses `--clean`. Comprueba conteos de las tablas históricas contra el origen y relaciones relevantes. Este ensayo sin propietarios prueba recuperación de datos; la recuperación operativa también necesita los roles/permisos originales.

Para Redis, utiliza otra instancia aislada de **la misma versión**, detenida y sin datos necesarios. Verifica `SHA256SUMS`; restaura el contenido completo de `redis-datos.tar.gz` en su directorio de datos, con propietario `redis`, y usa una copia de configuración adaptada a esa instancia. No conserves allí el bind de la IP de producción. Arranca y comprueba índices, conteos y persistencia. No apuntes la plataforma real a la instancia de ensayo.

## 6. Volver al entorno anterior

Si se decide revertir, primero detén API/web/worker nuevos y respalda sus datos si contienen trabajo que se deba conservar. Mantén las automatizaciones detenidas durante toda la reversión.

1. Restaura `cociber_ctf` desde el dump a una base **vacía**, con los roles existentes. No ejecutes `roles.sql` indiscriminadamente sobre el cluster actual: los roles se conservaron y pueden pertenecer a otras bases.
2. Restaura las reglas HBA anteriores de `cociber_app` y recarga PostgreSQL después de comprobar errores. Conserva la administración local.
3. Si necesitas los datos Redis anteriores, detén Redis y restaura el respaldo completo en un directorio preparado con los permisos originales. El respaldo contiene todos los índices: verifica que no sobrescribas datos nuevos de otros consumidores. No mezcles AOF actual con RDB antiguo.
4. Conserva las credenciales anteriores. El permiso añadido de Pub/Sub no obliga a rotarlas; puedes restaurar la ACL respaldada si necesitas reproducir exactamente la configuración previa.
5. Usa el `.env` y Compose históricos, verifica acceso y limpieza de sesiones antes de permitir nuevos jugadores. Rehabilita una automatización solo tras comprobar a qué versión apunta.

## Registro de aceptación

| Evidencia | Resultado a registrar |
| --- | --- |
| Host/fecha/operador | Completar al ejecutar |
| Ruta del respaldo y hashes | Privados; registrar ubicación, no contenido |
| Ensayo de restauración PostgreSQL/Redis | Correcto / pendiente, con fecha |
| Base anterior borrada | `cociber_ctf`; no otras bases |
| Redis limpiado | Índice y exclusividad verificados |
| Nueva conexión | `cociber_fresh`, Redis `/1`, `cociber_app` |
| Credenciales | Conservadas; no escribir valores |
| TLS/tabla/Redis/Lua/PubSub | Resultado de las pruebas de este documento |
| Plataforma y worker | Estado y pruebas reales pendientes |

No marques una prueba como correcta únicamente porque el comando esté documentado.
