# CoCiber: instalación nueva del refactor

Esta versión prepara una **base nueva**, según la decisión del propietario del proyecto. No migra, vacía ni renombra las tablas de la plataforma que ya está en servicio. No se ha desplegado en Nutanix desde este trabajo.

## Qué se puede usar y qué falta validar

| Área | Implementación | Condición antes de producción |
| --- | --- | --- |
| Esquema PostgreSQL | Tablas MAYÚSCULAS, prefijos únicos, UUID y corridas hex de 12 caracteres | Base vacía separada; respaldo y permisos revisados |
| Acceso | JWT, argon2id, bootstrap fuera de HTTP, cambio inicial obligatorio, revocación y límite de login | Secretos propios y TLS publicado verificado |
| Reservas | Cola persistente; índices únicos por reto, atacante y víctima | Cupo efectivo **1 por Kali**, no seis |
| Preparación | Reserva duradera → flag por stdin → check del hash → usuario Kali → conexión personal Guacamole | Helpers nuevos probados en las VM |
| Limpieza | Worker independiente, compensación y reintentos; una reserva no se libera si falla destroy | Instalar y supervisar la unidad del worker |
| ESC-02 / ESC-03 | Adaptador asyncssh y helpers nuevos incluidos | Deshabilitados por defecto; requieren instalación y prueba real |
| ESC-01 / ESC-04 / ESC-05 | Estrategias catalogadas y cerradas | Faltan contratos reales de reconocimiento, WinRM y Samba. No son ejercicios ejecutables todavía |
| Consola | Cliente oficial Guacamole dentro del reto, ticket HttpOnly, túnel del mismo origen, permiso READ de una conexión efímera | Prueba E2E contra Guacamole real pendiente |
| Publicación | Grupo asignado + piloto con verificación y limpieza exitosas | El piloto no concede puntos |
| Mantenimiento | Drenaje y confirmación solo después de prueba por consola | Snapshot manual en Prism; no se invoca una API no verificada |

El adaptador WinRM es deliberadamente un punto de extensión deshabilitado, **no una implementación operativa**. No se envían flags mediante `run_ps` ni en argumentos. La elección Windows A→B está confirmada, pero faltan el helper Windows y el transporte de stdin comprobado.

## Separación respecto de la instalación histórica

| Instalación | API | Interfaz | Compose | Configuración |
| --- | --- | --- | --- | --- |
| Histórica | `app.main:app` | `frontend/src/App.tsx` | `docker-compose.prod.yml` | `.env` existente |
| Nueva | `ctf.infrastructure.main:app` | `frontend/src/fresh/App.tsx` | `deploy/docker-compose.fresh.yml` | `.env.fresh` |

El Dockerfile incluye ambas implementaciones, pero el compose nuevo elige explícitamente la API y el frontend nuevos. **No combines los dos archivos Compose.** No ejecutes ambos frontends en el mismo puerto. El despliegue automático histórico continúa apuntando a la versión histórica; no publiques estos cambios pensando que cambia por sí solo de esquema.

La carpeta `backend/ctf` separa dominio, aplicación, adaptadores HTTP/PostgreSQL/Redis/Guacamole/inyección y composición de infraestructura. Se reutiliza el cliente Guacamole de `app/guacamole.py` y el único script de conciliación existente. Los módulos históricos siguen referenciados por su despliegue y sus pruebas; no son archivos basura.

## 1. Preparar configuración y base vacía

En LAB-CTFWEB, dentro del clon:

```bash
cp -n deploy/fresh.env.example .env.fresh
chmod 600 .env.fresh
nano .env.fresh
```

Completa las URLs de la **base nueva** y de Redis, la cuenta técnica de Guacamole y `JWT_SECRET` generado con `openssl rand -hex 32`. Codifica para URL los caracteres especiales de las contraseñas de PostgreSQL/Redis. No copies contraseñas de ejemplo ni reutilices la base histórica. El usuario de inicialización necesita crear tablas/extensión; la cuenta de ejecución necesita solamente el acceso operativo a esas tablas.

`PUBLIC_ORIGIN` es el origen visto por el navegador. `.20` y `.21` pertenecen a la misma interfaz de LAB-RTRFW; `.22` pertenece a otra interfaz de LAB-GUAC. Confirma terminación TLS, DNAT y puerto de Nginx con el equipo antes de publicar. El compose escucha por defecto en `.13:8081`; eso **no demuestra** que el DNAT `.21:443 → .13:443` termine ahí. Esta versión no modifica nftables ni crea un proxy TLS.

PostgreSQL y Redis siguen siendo nativos en LAB-DB-POSTGRES. No se agregan contenedores de BD. Se recomienda una base Redis lógica separada y ACL que permita las claves de esta aplicación; no ejecutar `FLUSHALL`.

```bash
sudo install -d -o root -g 10001 -m 0750 /opt/cociber-secrets
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml build api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli init-db --empty-database
```

`init-db` rechaza una base que ya contiene tablas y no las borra. Como alternativa, el administrador de BD puede revisar y ejecutar `deploy/schema/cociber_fresh.sql` en la base vacía. **Elige una vía, no ejecutes ambas.** El diccionario completo está en [DICCIONARIO_FRESH.md](DICCIONARIO_FRESH.md).

## 2. Crear el primer administrador

```bash
sudo bash scripts/crear_admin.sh
```

Solicita la clave sin mostrarla. También acepta `ADMIN_CTF_USERNAME` y `ADMIN_CTF_PASSWORD` de `.env.fresh`. Rechaza crear otro administrador si ya existe uno. Para bootstrap de arranque se puede poner `BOOTSTRAP_ADMIN=true` una sola vez; después volver a `false` y retirar la contraseña de esa configuración. El primer acceso obliga a cambiarla. La API web nunca acepta rol administrador al crear usuarios.

No se han incorporado al repositorio las credenciales iniciales proporcionadas en el documento del usuario.

## 3. Arrancar y conciliar fichas

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli check
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml up -d --force-recreate --wait --wait-timeout 180 api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python reconcile_nutanix_inventory.py --fresh
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python reconcile_nutanix_inventory.py --fresh --apply
```

La conciliación usa el catálogo de nombres/IP confirmado en el proyecto. **No consulta Prism**, no crea MV ni confirma conectividad. Las fichas nacen `planned`. Si encuentra una dirección distinta u ocupada, detiene la aplicación de cambios. El administrador revisa las MV reales y después marca su ficha disponible.

Puedes preparar explícitamente los dos laboratorios y los cinco retos como **borradores**, sin activar integraciones ni publicar:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli configure-catalog
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli configure-catalog --apply
```

El primer comando muestra el plan; el segundo crea solo lo que falta. Conserva retos existentes y rechaza combinaciones de víctima/estrategia incompatibles. ESC-01/04/05 quedan como pendientes deshabilitados aunque su borrador ya exista.

## 4. Instalar y probar los helpers

Sigue [HELPERS_FRESH.md](HELPERS_FRESH.md). No reemplaces `ctf-dvwa-flag`, `ctf-ssh-practice.py` ni los archivos de las demos anteriores. El contrato nuevo tiene nombres y run_id diferentes.

Las claves del host montadas para el usuario API 10001 deben ser legibles por ese UID. Ejemplo: propietario root, grupo numérico 10001, modo 0640, directorio 0750. Es la misma distinción tratada anteriormente: OpenSSH ejecutado como root puede rechazar una clave privada 0640; para una prueba manual usa una copia temporal 0600. AsyncSSH dentro del contenedor necesita lectura real de su montaje y `known_hosts` verificado.

```bash
sudo bash scripts/probar_inyector.sh LAB-LNXVICT SSH-PASSWORD-LAB
sudo bash scripts/probar_inyector.sh LAB-SRVWEB DVWA-SQLI-LAB
```

Cada prueba drena la máquina, rechaza corridas vivas y ejecuta create/check/destroy sin imprimir la flag. Deja la ficha en mantenimiento para revisión administrativa. Solo después de aprobar estas pruebas configura `SSH_INJECTOR_ENABLED=true` y, para ESC-03, `DVWA_LAB_ENABLED=true`. Recrea la API y el worker al cambiar estas variables.

## 5. Proceso único de cola y limpieza

API y web son los dos servicios del compose. La limpieza se ejecuta en **otro proceso** usando la imagen API, supervisado por systemd; nunca dentro de un worker de Uvicorn.

```bash
sudo nano deploy/systemd/cociber-fresh-worker.service
# Revisa WorkingDirectory: debe apuntar a tu clon real.
sudo install -m 0644 deploy/systemd/cociber-fresh-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cociber-fresh-worker.service
sudo systemctl status cociber-fresh-worker.service --no-pager
```

Un advisory lock PostgreSQL impide dos procesos de limpieza simultáneos. Al reiniciar, una reserva interrumpida se compensa antes de reutilizar sus recursos. Si Guacamole o la víctima no responden, la corrida permanece `reiniciando`; se reintenta sin concederla a otro jugador. No cambies ese estado manualmente para saltar una limpieza fallida.

Diagnóstico puntual, **con la unidad detenida**:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.worker --once
```

## 6. Preparar una demo desde la web

1. Entra como administrador y cambia la clave inicial.
2. En **Máquinas**, revisa fichas y marca disponibles las Kali y las víctimas verificadas. Una Kali tiene un único cupo; el backend elige la primera libre.
3. En **Laboratorios**, crea `LAB-ATACANTES` para VLAN20 y `LAB-VICTIMAS` para VLAN30 usando las fichas existentes, o utiliza los creados por configure-catalog. Confirma cada laboratorio disponible después de verificar al menos una de sus máquinas. Solo las máquinas individualmente ready serán asignables; las futuras víctimas pueden seguir planned. No se escribe una IP manual.
4. En **Usuarios**, crea `demo.blue` y `demo.purple` con claves privadas independientes. Su primer login también exige cambiarlas. No se crean usuarios de Guacamole permanentes: cada corrida genera uno efímero.
5. En **Grupos**, crea `CTF-DEMO-2026` y selecciona ambos jugadores.
6. En **Retos**, usa los borradores creados por configure-catalog o crea `ESC-02-BRUTEFORCE` y `ESC-03-WEBEXPLOIT` si todavía no existen. El código conocido completa estrategia/dificultad; selecciona su víctima y un nombre. Los cuatro campos visibles son código, nombre, dificultad y víctima. Las opciones avanzadas contienen puntos, tiempo, pistas y recursos.
7. Selecciona cada reto, asigna el grupo, ejecuta el piloto y observa **Corridas**. Debe terminar liberada con resultado resuelta; luego se habilita Publicar. El piloto verifica el hash y prueba la creación de la conexión Guacamole, pero una revisión humana de la consola real sigue siendo necesaria.
8. Entra como jugador. Solo verá los retos publicados de su grupo. Inicia uno, espera preparación, investiga desde la consola embebida y envía su flag. La puntuación se registra una sola vez por usuario/reto.

Después de un ejercicio DVWA real la VM queda `dirty` por política conservadora. No vuelve a asignarse hasta restauración, prueba y confirmación. Un piloto que solo provisiona/verifica/limpia no marca la VM dirty.

## 7. Redis, errores y comprobaciones

| Clave | Tipo / TTL | Uso |
| --- | --- | --- |
| `lock:reto:{uuid}` | string / 120 s | Candado complementario a PostgreSQL |
| `lock:maquina:{uuid}` | string / duración de corrida | Reserva complementaria de atacante |
| `jwt:revocado:{jti}` | string / vida restante JWT | Logout |
| `ranking:global` | sorted set / sin TTL | Caché reconstruida por el worker |
| `rate:login:{sha256_usuario}` | contador / 60 s | Límite de login y envíos; sin claves arbitrarias del cliente |
| `terminal:ticket:{sha256_ticket}` | string / 45 s | Ticket de un solo uso; nunca JWT en URL |
| `terminal:session:{run_id}` | string cifrada / 7200 s | Token personal Guacamole |
| `ws:canal:ranking` | pub/sub | Actualización de ranking |

La cola está en **CORRIDAS**, estado `en_cola`, no en una lista Redis: así sobrevive a un reinicio o pérdida de Redis. No se introduce una segunda fuente de verdad. Los locks Redis se liberan con comparación del propietario, no con DEL indiscriminado.

Las sondas de dependencias reintentan hasta tres veces con backoff y abren un circuito de 10 s si fallan. No se reintentan automáticamente escrituras o inyecciones no idempotentes. `/api/v1/health` informa proceso vivo; `/api/v1/health/ready` informa PostgreSQL y Redis. Los errores de operaciones siguen `error_code`, `message`, `correlation_id`; la auditoría omite flags, contraseñas y trazas. Si la propia BD está caída, la auditoría no puede persistirse: se emite solo el identificador de correlación y el código en el registro local.

## 8. Backups y actualizaciones

Configura `~/.pg_service.conf` y un `PGPASSFILE` privado con permisos 0600 en el host que ejecutará `pg_dump`. Usa cliente PostgreSQL compatible con el servidor 16. Prueba restauración en una base aparte; que `pg_restore --list` pase valida el contenedor del backup, no sustituye una restauración completa.

```bash
PGSERVICE=cociber PGPASSFILE=/ruta/privada/.pgpass BACKUP_DIR=/srv/backups/cociber bash scripts/backup_db.sh
```

Agenda ese comando a diario en cron del operador, por ejemplo a las 02:00 en la zona horaria del servidor. Conserva siete días. El script borra únicamente archivos `cociber-*.dump` del directorio de backup indicado y solo después de producir y listar un backup nuevo correctamente.

Para actualizar, drena los laboratorios, cierra las corridas vivas y realiza backup. Detén la unidad del worker, ejecuta `bash scripts/actualizar_produccion.sh` y vuelve a iniciarla. El script exige Git limpio y fast-forward; no ejecuta migraciones de esquema. Si hay cambios de esquema en una futura versión, requieren una migración explícita antes del arranque.

## 9. Límites de esta entrega

- El esquema nuevo y las rutas HTTP no son compatibles con la BD histórica. No apuntes el compose nuevo a esa base.
- No se ejecutaron instalaciones en víctimas, cambios de firewall, Prism ni Guacamole real. La prueba E2E SSH/DVWA/Guacamole queda para el entorno del operador.
- Los escenarios 01/04/05 requieren contratos reales; no se publican por un interruptor que finja que ya funcionan.
- Por decisión del usuario, su habilitación queda para otra fase; las [guías de recopilación y el registro de pendientes](PENDIENTES_ESCENARIOS.md) detallan qué entregar.
- La conciliación conserva su alcance local; no es un inventario obtenido de la API de Nutanix.
- La navegación usa vistas SPA con rutas `/admin/maquinas`, `/admin/laboratorios`, `/admin/retos`, `/admin/mantenimiento` y las otras secciones; el proxy debe conservar el fallback a index.html.
- El catálogo inicial se configura por formulario o con configure-catalog explícito. No se insertan cuentas o retos ficticios al arrancar.

Referencias técnicas usadas: [AsyncSSH](https://asyncssh.readthedocs.io/en/latest/), [cliente JavaScript de Guacamole](https://guacamole.apache.org/doc/gug/guacamole-common-js.html), [índices parciales PostgreSQL 16](https://www.postgresql.org/docs/16/indexes-partial.html).
