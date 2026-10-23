# Guía sencilla: actualizar Cociber CTF en Ubuntu 26.04

**Destino:** máquina de la aplicación `10.10.10.13`. Las bases PostgreSQL 16 y Redis 7 **ya existen** en `LAB-DB-POSTGRES (10.10.10.14)` y se usan como servicios nativos. Apache Guacamole funciona en su infraestructura **independiente**: no cambiar su servidor, configuración, datos ni credenciales.

## Antes de empezar: ¿qué actualiza esta guía?

Solo actualiza dos contenedores: `api` (FastAPI) y `web` (Nginx/React). El archivo `docker-compose.prod.yml` **no contiene** PostgreSQL, Redis ni Guacamole. El `docker-compose.yml` antiguo permanece intacto para desarrollo en Windows.

**No ejecutar:** `docker compose down -v`, `docker volume prune`, `docker system prune --volumes`, `git reset --hard` ni scripts de instalación de bases sobre datos existentes. No ejecutar el SQL inicial de 19 tablas sobre una base poblada.

## Paso 1 — Verificar las bases y hacer respaldo

En `10.10.10.14`, primero comprobar que estén activos:

```bash
sudo systemctl is-active postgresql@16-main.service
sudo systemctl is-active cociber-redis.service
```

Los respaldos de producción se hacen con el **repositorio separado** [cociber-ctf-deploy](https://github.com/lavillamarin3-hash/cociber-ctf-deploy), según [la guía de PostgreSQL/Redis](https://github.com/lavillamarin3-hash/cociber-ctf-deploy/blob/main/docs/09_RESPALDOS_POSTGRES_REDIS.md). El script `scripts/respaldo_ctf_nativo.sh` exige una **ruta externa existente y protegida**; produce `postgres_ctf.dump`, `redis_ctf.rdb`, hashes y un inventario de roles. Verifica el resultado y copia el respaldo fuera de la VM. No subas dumps a Git.

No se realiza ninguna restauración en producción durante esta actualización.

## Paso 2 — Comprobar la aplicación, sin perder su configuración

En la VM web `10.10.10.13`, entrar en la carpeta **real** donde ya está clonado el proyecto. Si todavía no existe una copia, clonar:

```bash
git clone https://github.com/lavillamarin3-hash/ctf-platform.git
cd ctf-platform
```

Si ya existe, entrar en ella en lugar de clonar. Comprobar:

```bash
git status --short
git remote -v
git rev-parse HEAD
```

Anota el commit actual para poder volver a esa versión. **Si `git status --short` muestra cambios, revisarlos antes de actualizar**. No sobrescribir archivos propios ni borrar `.env`.

Actualizar solamente después de que la rama de producción haya sido aprobada/incorporada a `main`:

```bash
git pull --ff-only origin main
```

Este comando descarga código; no toca la base de datos.

## Paso 3 — Configurar variables SIN reemplazar Guacamole

Si es la primera instalación y no existe `.env`:

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

**Si `.env` ya existe, NO ejecutar `cp`; editarlo y conservar los secretos y ajustes actuales**. Asegurar los siguientes valores, usando URLs privadas reales de los servicios ya provisionados (las claves se codifican como URL, nunca se publican):

```dotenv
WEB_BIND_IP=10.10.10.13
WEB_PORT=8081
DATABASE_URL=postgresql+asyncpg://cociber_app:CLAVE_URL_CODIFICADA@10.10.10.14:5432/cociber_ctf?ssl=require
REDIS_URL=redis://cociber_app:OTRA_CLAVE_URL_CODIFICADA@10.10.10.14:6379/0
MANAGE_SCHEMA_ON_STARTUP=false
CTF_SEED_DEMO_DATA=false
PUBLIC_ORIGIN=http://10.10.10.13:8081
```

Estos son **ejemplos con marcadores**, no credenciales funcionales. La herramienta privada `tools/write_application_env.py` del repositorio `cociber-ctf-deploy` puede generar las URL correctas sin escribir claves en público. Usa las cuentas `cociber_app`; **no** uses la administrativa `cociberctf` para la API. Redis usa TCP autenticado en red privada restringida; para otra red se requiere TLS.

Mantener los mismos `JWT_SECRET`, `FIELD_HMAC_SECRET`, `GUACAMOLE_MODE`, `GUACAMOLE_BASE_URL`, `GUACAMOLE_API_URL`, cuenta/contraseña de servicio de Guacamole y parámetros SSH que ya funcionan. No se actualiza ni se reinicia el servidor Guacamole. Para uso público, situar la web tras un proxy HTTPS y adaptar `PUBLIC_ORIGIN`; HTTP es solo ejemplo de acceso en la LAN.

## Paso 4 — Verificar ANTES de iniciar

```bash
chmod 600 .env
python3 scripts/verificar_entorno_produccion.py
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml ps
sudo ss -lntp | grep ':8081 ' || true
```

La primera comprobación **no hace conexiones**. Si `8081` está ocupado por la web anterior, no intentes iniciar dos servicios en el mismo puerto: prueba temporalmente con otro `WEB_PORT` o planifica el cambio sin detener PostgreSQL/Redis. **No ejecutes `docker compose config` sin `--quiet` en una terminal compartida**, porque puede mostrar secretos.

Si esta es la primera instalación, la comprobación de `ps` puede mostrar que aún no hay servicios: es normal.

## Paso 5 — Probar acceso a bases desde el contenedor (solo lectura)

Después de compilar la API:

```bash
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml run --rm --no-deps -T api python -c 'import asyncio,os; from sqlalchemy import text; from sqlalchemy.ext.asyncio import create_async_engine; import redis.asyncio as redis
async def probar():
    engine=create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        cliente=redis.from_url(os.environ["REDIS_URL"])
        try:
            assert await cliente.ping()
        finally:
            await cliente.aclose()
        print("PostgreSQL y Redis responden desde la API")
    finally:
        await engine.dispose()
asyncio.run(probar())'
```

Esta prueba envía `SELECT 1` y `PING`: no modifica tablas ni claves. Si falla, comprobar permisos, red, TLS y credenciales en privado. **No iniciar aún la web si falla**.

## Paso 6 — Iniciar o actualizar SOLO web y API

Durante la ventana autorizada, sin sesiones de estudiantes abiertas:

```bash
docker compose -f docker-compose.prod.yml up -d --build api web
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=80 api web
```

No uses el Compose anterior para la producción. La aplicación debe responder en `http://10.10.10.13:8081` (o en el dominio/puerto privados configurados). Comprueba login, listado y asignación de retos, estudiantes, flags, ranking y acceso por terminal mediante el Guacamole **ya existente**. No se considera terminado solo porque cargue la página.

## Paso 7 — Si hay un fallo

Conserva `.env` y los respaldos. Anota el commit previo del paso 2. Para volver al código anterior, en una **ventana controlada**, utiliza una rama de recuperación creada desde el commit conocido y recompila únicamente la aplicación. Antes, comprueba que ese commit admite la misma configuración de producción y que no depende de iniciar contenedores de base de datos. **No reviertas ni restaures la base productiva como mecanismo de rollback de la web**.

Los archivos `.env`, `.dump`, `.rdb`, claves y respaldos no deben guardarse en GitHub. Para restaurar datos utiliza un servidor aislado y el procedimiento del repositorio de despliegue.

## Diferencia entre entornos

| Entorno | Comando de Compose | Servicios administrados |
| --- | --- | --- |
| Windows/desarrollo | `docker compose -f docker-compose.yml up -d` | `postgres`, `redis`, `api`, `web` |
| Ubuntu/producción | `docker compose -f docker-compose.prod.yml up -d --build api web` | Solo `api` y `web` |

**Validación pendiente:** hay que ejecutar estas pruebas en `10.10.10.13` y `10.10.10.14`. Revisar código/archivos o aprobar un Pull Request no demuestra que las VM ya estén desplegadas.
