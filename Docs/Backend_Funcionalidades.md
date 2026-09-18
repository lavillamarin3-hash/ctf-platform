# Backend — Funcionalidades y API
> **Fuente:** `backend/app/` · **Generado:** 2026-09-17 · **Estado:** MVP funcional

---

## Tabla de Contenidos

1. [Stack y dependencias](#1-stack-y-dependencias)
2. [Estructura de módulos](#2-estructura-de-módulos)
3. [Ciclo de vida de la aplicación](#3-ciclo-de-vida-de-la-aplicación)
4. [Catálogo completo de endpoints](#4-catálogo-completo-de-endpoints)
5. [Casos de uso implementados](#5-casos-de-uso-implementados)
6. [Arquitectura Hexagonal — Puertos y Adaptadores](#6-arquitectura-hexagonal--puertos-y-adaptadores)
7. [Seguridad y control de acceso](#7-seguridad-y-control-de-acceso)
8. [Gestión de estado en tiempo real](#8-gestión-de-estado-en-tiempo-real)
9. [Modelo de datos relacional](#9-modelo-de-datos-relacional)
10. [Variables de entorno](#10-variables-de-entorno)
11. [Brecha con el MVP objetivo](#11-brecha-con-el-mvp-objetivo)

---

## 1. Stack y Dependencias

| Componente | Librería | Versión |
|---|---|---|
| Framework web | FastAPI | `>=0.115,<1` |
| Servidor ASGI | Uvicorn (con `standard`) | `>=0.30,<1` |
| ORM async | SQLAlchemy 2.0 | `>=2.0,<3` |
| Driver PostgreSQL | asyncpg | `>=0.29,<1` |
| Validación/Config | Pydantic Settings | `>=2.0,<3` |
| Autenticación JWT | PyJWT | `>=2.8,<3` |
| Hash contraseñas | argon2-cffi | `>=23.1,<26` |
| Caché / Rate limit | redis (async) | `>=5.0,<7` |
| Upload multipart | python-multipart | `>=0.0.9,<1` |
| Validación email | email-validator | `>=2.0,<3` |

**Runtime:** Python 3.12-slim · **Puerto:** 8000 · **Usuario:** `appuser` (UID 10001, no root)

---

## 2. Estructura de Módulos

`
backend/app/
├── __init__.py       — Marca el paquete; expone la versión "0.1.0"
├── core.py           — Infraestructura transversal: JWT, Argon2, HMAC, RBAC, Settings
├── db.py             — Engine SQLAlchemy async + migraciones idempotentes en startup
├── models.py         — 12 entidades ORM (SQLAlchemy Mapped, declarative)
├── schemas.py        — ~30 clases Pydantic v2 (contratos I/O de la API)
├── guacamole.py      — Adaptadores HTTP Apache Guacamole (Port & Adapter pattern)
└── main.py           — FastAPI app: ciclo de vida, ~60 endpoints, WebSocket, audit
`

### Responsabilidades por módulo

| Módulo | Responsabilidad única (SRP) |
|---|---|
| `core.py` | Seguridad transversal: tokens JWT, hashing Argon2, HMAC submissions, dependencias de autenticación FastAPI |
| `db.py` | Crear engine async, session factory y ejecutar `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE IF NOT EXISTS` |
| `models.py` | Declarar entidades SQLAlchemy y sus relaciones; **sin lógica de negocio** |
| `schemas.py` | Validar y tipar los contratos de entrada/salida con Pydantic; **sin acceso a BD** |
| `guacamole.py` | Encapsular toda comunicación HTTP con Apache Guacamole detrás de interfaces abstractas |
| `main.py` | Coordinar todo lo anterior: ciclo de vida, rutas, lógica de negocio inline, WebSocket broadcast |

> **Nota actual:** `main.py` (1 676 líneas) concentra lógica de negocio, queries SQL y presentación en el mismo archivo. Ver [sección 11](#11-brecha-con-el-mvp-objetivo) para el plan de refactoring.

---

## 3. Ciclo de Vida de la Aplicación

El `lifespan` de FastAPI (gestor de contexto async) inicializa los siguientes recursos compartidos en `app.state`:

`
startup
  ├── session_factory    ← async_sessionmaker de SQLAlchemy
  ├── create_schema()    ← CREATE TABLE / ALTER TABLE idempotentes
  ├── seed_data()        ← Roles + laboratorios + 17 retos de demostración
  ├── redis              ← Pool async (rate limiting + pub/sub)
  ├── guacamole          ← RemoteAccessProvisioningAdapter (stub o live)
  ├── guacamole_admin    ← GuacamoleAdminAdapter (stub o live)
  └── sockets            ← ConnectionManager (set de WebSockets activos)

shutdown
  └── redis.aclose()
`

### Datos sembrados (seed) en startup

| Entidad | Cantidad |
|---|---|
| Roles del sistema | 4 (admin, instructor, player, guest) |
| Laboratorios | 2 (LAB-ATACANTES VLAN 20, LAB-VICTIMAS VLAN 30) |
| VMs de laboratorio | 8 en total (3 atacantes, 5 víctimas) |
| Retos de demostración | 17 (WEB, CRY, FOR, REV, PWN, OSI, STE, MISC, LAB) |

---

## 4. Catálogo Completo de Endpoints

### 4.1 Salud y Autenticación

| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/health` | Público | Retorna `{"status":"ok","service":"ctf-api"}` |
| `POST` | `/api/v1/auth/login` | Público | Autenticación con usuario/contraseña. Rate limit: 10 req/min por username. Retorna JWT access token + perfil de usuario |
| `GET` | `/api/v1/auth/me` | Autenticado | Retorna el perfil del usuario actual desde el token JWT |
| `PATCH` | `/api/v1/auth/profile` | Autenticado | Actualiza `username` y `email` del propio perfil. Verifica unicidad |
| `POST` | `/api/v1/auth/password` | Autenticado | Cambia la contraseña verificando la actual. Almacena nuevo hash Argon2 |

**Payload login:**
`json
{ "username": "player01", "password": "MiContrasena123!" }
`

**Respuesta login:**
`json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "user": { "id": 1, "username": "player01", "role": "player", "is_active": true }
}
`

---

### 4.2 Retos (Challenges)

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/challenges` | Todos autenticados | Lista retos con filtros opcionales: `?difficulty=`, `?category=`, `?mitre=`. Jugadores ven solo los asignados a sus grupos activos. Guest: sin instrucciones |
| `GET` | `/api/v1/categories` | Todos autenticados | Lista categorías disponibles con conteo de retos publicados |
| `POST` | `/api/v1/challenges` | admin, instructor | Crea un nuevo reto con código único |
| `PUT` | `/api/v1/challenges/{code}` | admin, instructor | Actualiza todos los campos de un reto existente |
| `DELETE` | `/api/v1/challenges/{code}` | admin, instructor | **Archiva** el reto (`is_published=False`); no elimina de BD |

**Categorías válidas:** WEB · CRIPTOGRAFÍA · FORENSE · REVERSING · PWN / EXPLOITING · OSINT · ESTEGANOGRAFÍA · MISC

**Dificultades válidas:** Básico · Medio · Avanzado

---

### 4.3 Flags (Banderas de Reto)

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/challenges/{code}/flags` | admin, instructor | Lista todas las flags (incluye metadatos, NO valores en claro) |
| `POST` | `/api/v1/challenges/{code}/flags` | admin, instructor | Crea flag. Modo `static`: requiere `value` (hashea con Argon2). Modo `dynamic`: requiere `template` con variables `{{CODE}}`, `{{USER}}`, `{{RUN_ID}}`, `{{RAND}}` |
| `PUT` | `/api/v1/challenges/{code}/flags/{flag_id}` | admin, instructor | Actualiza flag. Cambio a `dynamic` limpia `ChallengeRunFlag` previos |
| `DELETE` | `/api/v1/challenges/{code}/flags/{flag_id}` | admin, instructor | Elimina permanentemente una flag |

**Modos de flag:**

| Modo | Almacenamiento | Validación |
|---|---|---|
| `static` | `flag_hash` (Argon2id) en `challenge_flags` | `verify_password(submitted, flag.flag_hash)` |
| `dynamic` | `flag_hash` por instancia en `challenge_run_flags` | `verify_password(submitted, run_flag.flag_hash)` |

---

### 4.4 Ejecución de Retos (Runs)

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/challenges/{code}/start` | player | Inicia sesión de reto con TTL de 90 minutos. Verifica asignación al grupo, busca VM disponible, genera flags dinámicas, retorna URL de Guacamole |
| `GET` | `/api/v1/runs` | player, admin, instructor | Lista últimas 30 sesiones. Players: solo las propias |
| `POST` | `/api/v1/runs/{run_id}/close` | player | Cierra sesión activa y revoca acceso en Guacamole |

**Flujo de inicio (`start`):**
`
1. Rate limit: 6 req/min por (user_id, code)
2. Verificar reto publicado y asignado al grupo del jugador
3. Crear ChallengeRun (status="active", TTL=90min)
4. Buscar VM via asset_references del reto
   ├── Si hay UserVMConnection personal → usar esa conexión
   ├── Si hay VM pero sin conexión personal → HTTP 409
   └── Si no hay VM → usar provision() del adaptador Guacamole
5. Generar ChallengeRunFlag para flags dinámicas
6. Crear RemoteAccessAssignment con launch_url
7. Escribir AuditEvent
`

---

### 4.5 Envío de Flags (Submissions)

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/challenges/{code}/submissions` | player | Valida flag enviada por el jugador |

**Flujo completo de validación:**
`
1. Rate limit: 8 req/min por (user_id, code)
2. Verificar reto publicado y asignado al grupo
3. Verificar ChallengeRun activo y no expirado
4. Para cada flag activa del reto:
   ├── dynamic: busca ChallengeRunFlag del run → verify_password()
   └── static:  verify_password(submitted, challenge_flag.flag_hash)
5. Registrar Submission con HMAC del valor (nunca en claro)
6. Si match: verificar si TODAS las flags activas fueron correctas
   └── Si completo por primera vez:
       ├── Crear ChallengeCompletion con awarded_points
       ├── Broadcast WebSocket: ranking.updated
       └── Publicar en Redis canal ctf:ranking
`

---

### 4.6 Usuarios

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/users` | admin | Lista todos los usuarios del sistema |
| `GET` | `/api/v1/users/visible` | admin, instructor | Instructores no ven cuentas de administrador |
| `POST` | `/api/v1/users` | admin | Crea usuario en BD + Guacamole (rollback atómico si falla) |
| `PATCH` | `/api/v1/users/{id}` | admin | Actualiza rol/estado. Protecciones: no puede auto-deshabilitar, >=1 admin activo siempre |
| `DELETE` | `/api/v1/users/{id}` | admin | Elimina de BD y Guacamole. No puede eliminar su propia cuenta |

---

### 4.7 Grupos de Estudiantes

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/groups` | admin, instructor | Lista grupos con miembros y retos asignados |
| `POST` | `/api/v1/groups` | admin | Crea grupo + UserGroup en Guacamole |
| `PATCH` | `/api/v1/groups/{id}` | admin | Actualiza grupo y sincroniza con Guacamole |
| `DELETE` | `/api/v1/groups/{id}` | admin | Elimina grupo + re-sincroniza permisos de ex-miembros |
| `POST` | `/api/v1/groups/{id}/members` | admin | Añade jugador activo. Sincroniza Guacamole |
| `DELETE` | `/api/v1/groups/{id}/members/{uid}` | admin | Quita miembro. Re-sincroniza Guacamole |
| `PUT` | `/api/v1/challenges/{code}/groups/{gid}` | admin, instructor | Asigna reto a grupo |
| `DELETE` | `/api/v1/challenges/{code}/groups/{gid}` | admin, instructor | Desasigna reto del grupo |
| `GET` | `/api/v1/groups/{id}/remote-connections` | admin, instructor | Lista conexiones individuales Guacamole del grupo |
| `POST` | `/api/v1/groups/{id}/remote-connections` | admin | Clona conexión Guacamole para cada miembro del grupo |
| `DELETE` | `/api/v1/groups/{id}/remote-connections/{uid}` | admin | Elimina conexión Guacamole personal de un miembro |

---

### 4.8 Laboratorios y VMs

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/laboratories` | admin, instructor | Lista labs con VMs |
| `GET` | `/api/v1/player/laboratories` | player | Labs y VMs accesibles al jugador (filtrados por retos asignados). Incluye URL Guacamole personal |
| `POST` | `/api/v1/laboratories` | admin | Crea laboratorio |
| `PATCH` | `/api/v1/laboratories/{id}` | admin | Actualiza laboratorio |
| `DELETE` | `/api/v1/laboratories/{id}` | admin | Elimina laboratorio y sus VMs (cascade) |
| `POST` | `/api/v1/vms` | admin | Registra VM. Valida IP contra catálogo y unicidad |
| `PATCH` | `/api/v1/vms/{id}` | admin | Actualiza VM |
| `DELETE` | `/api/v1/vms/{id}` | admin | Elimina VM |

---

### 4.9 Administración Guacamole

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/admin/guacamole/status` | admin | Estado del adaptador Guacamole |
| `GET` / `POST` | `/api/v1/admin/guacamole/users` | admin | Listar / crear usuarios Guacamole |
| `PATCH` / `DELETE` | `/api/v1/admin/guacamole/users/{user}` | admin | Actualizar / eliminar usuario Guacamole |
| `GET` / `PATCH` | `/api/v1/admin/guacamole/users/{user}/permissions` | admin | Obtener / actualizar permisos de sistema y conexiones |
| `GET` / `POST` | `/api/v1/admin/guacamole/connections` | admin | Listar / crear conexiones (SSH, RDP, VNC) |
| `PUT` / `DELETE` | `/api/v1/admin/guacamole/connections/{id}` | admin | Actualizar / eliminar conexión |

---

### 4.10 Ranking, Reportes y Progreso

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/ranking` | Todos autenticados | Ranking de jugadores (puntos DESC, tiempo ASC) |
| `GET` | `/api/v1/progress` | player | Puntos totales y retos completados propios |
| `GET` | `/api/v1/reports/progress` | admin, instructor | Matriz progreso usuario×reto. Filtrable por `?group_id=` |
| `GET` | `/api/v1/reports/ranking.csv` | admin, instructor | Exporta ranking en CSV adjunto |
| `WebSocket` | `/api/v1/ws/ranking?token=<JWT>` | Autenticado | Actualizaciones de ranking en tiempo real |

---

## 5. Casos de Uso Implementados

### CU-01: Autenticación y Sesión
Login con Argon2id → JWT (20 min) → `Authorization: Bearer` → `get_current_user()` valida en cada request consultando el usuario en BD (rol e is_active en tiempo real).

### CU-02: Exploración del Catálogo
Jugadores ven solo retos asignados a sus grupos activos. Guest recibe el catálogo sin instrucciones ni referencias de activos. La respuesta incluye `completed: bool` calculado contra `challenge_completions`.

### CU-03: Iniciar Reto con Acceso a VM
El jugador inicia el reto → el sistema encuentra la VM via `asset_references` → retorna la URL de Guacamole personal → el jugador accede a la VM directamente desde el navegador con su sesión.

### CU-04: Validación de Flags
Las flags se verifican con Argon2id sin exponerse en claro. El sistema soporta múltiples flags por reto (todas deben responderse para completar), y flags dinámicas por instancia de usuario (anti-sharing).

### CU-05: Ranking en Tiempo Real
Al completar un reto → recálculo del ranking → broadcast WebSocket a todos los clientes + publicación en Redis. El cliente actualiza el scoreboard sin necesidad de polling.

### CU-06: Gestión de Grupos y Acceso
Admin crea grupos académicos (sincronizados con Guacamole) → añade jugadores → asigna retos → clona conexiones Guacamole individuales para cada miembro → los jugadores reciben acceso READ a su propia instancia de conexión.

### CU-07: Monitoreo de Progreso
Instructor consulta la matriz usuario×reto por grupo: estado (Completado/No iniciado), intentos, puntos obtenidos y timestamp de completación. Exportación CSV disponible.

---

## 6. Arquitectura Hexagonal — Puertos y Adaptadores

### Puertos definidos en `guacamole.py`

`python
class RemoteAccessProvisioningPort:
    async def provision(username, challenge_code, run_id) -> RemoteConnection: ...
    async def revoke(external_reference) -> None: ...

class GuacamoleAdminPort:
    # 18 métodos: usuarios, grupos, conexiones, permisos
    async def create_user(username, password, ...) -> GuacamoleUser: ...
    async def clone_connection(source_id, *, name) -> GuacamoleConnection: ...
    async def patch_user_permissions(username, ...) -> dict: ...
    # ...
`

### Adaptadores implementados

| Adaptador | Clase | Uso |
|---|---|---|
| Stub Provisioning | `StubGuacamoleAdapter` | Desarrollo / CI |
| Live Provisioning | `GuacamoleAdapter` | Producción |
| Stub Admin | `StubAdminAdapter` | Desarrollo / CI |
| Live Admin | `GuacamoleAdminAdapter` | Producción |

### Selección de adaptador (Factory)

`python
# Settings: guacamole_mode = "stub" | "live"
def make_guacamole_adapter() -> RemoteAccessProvisioningPort:
    return GuacamoleAdapter(...) if settings.guacamole_mode == "live" else StubGuacamoleAdapter()

def make_guacamole_admin() -> GuacamoleAdminPort:
    return GuacamoleAdminAdapter(...) if settings.guacamole_mode == "live" else StubAdminAdapter()
`

### Puertos pendientes de extraer (MVP objetivo)

| Puerto (a crear) | Estado actual |
|---|---|
| `ChallengeRepository` | Queries inline en `main.py` |
| `UserRepository` | Queries inline en `main.py` |
| `FlagValidatorPort` (Strategy) | `if/elif` inline en `submit_flag()` |
| `RankingRepository` | Función `ranking_rows()` con SQL directo |

---

## 7. Seguridad y Control de Acceso

### Rate Limiting (Redis)

| Operación | Límite | Clave Redis |
|---|---|---|
| Login | 10 req/60s por username | `rate:login:{username}` |
| Submit flag | 8 req/60s por (user_id, code) | `rate:flag:{user_id}:{code}` |
| Iniciar reto | 6 req/60s por (user_id, code) | `rate:start:{user_id}:{code}` |

Degradación graceful: si Redis no disponible, la operación continúa (Redis mejora seguridad, no la bloquea).

### Protección de datos sensibles

| Dato | Mecanismo |
|---|---|
| Contraseñas | Argon2id (resistente a GPU/ASIC) |
| Flags en BD | Argon2id; valor real nunca almacenado |
| Sumisiones en BD | HMAC-SHA256; permite deduplicar sin exponer el valor enviado |
| JWT | HS256 + `iss="lab-ctf-platform"` + `exp` 20 min |
| Cuenta de servicio Guacamole | Endpoint protegido contra eliminación y administración |

---

## 8. Gestión de Estado en Tiempo Real

### WebSocket `/api/v1/ws/ranking`

- **Autenticación:** JWT como query param `?token=<JWT>`; si inválido → cierre código 1008
- **Conexión:** El cliente recibe el ranking completo al conectarse
- **Eventos:** `{"type": "ranking.updated", "rows": [...]}`
- **Broadcast:** `ConnectionManager` itera sobre todos los WebSocket activos; elimina conexiones muertas automáticamente
- **Redis pub/sub:** También publica en canal `ctf:ranking` para compatibilidad con múltiples instancias

---

## 9. Modelo de Datos Relacional

| Tabla | Descripción |
|---|---|
| `roles` | Catálogo de 4 roles del sistema |
| `users` | Usuarios con hash Argon2, rol, estado, metadatos |
| `challenges` | Retos con MITRE technique, categoría, escenario |
| `challenge_flags` | Flags por reto (Argon2 hash, modo static/dynamic) |
| `challenge_run_flags` | Flags dinámicas por instancia de ejecución |
| `submissions` | Historial de envíos (HMAC del valor, resultado booleano) |
| `challenge_completions` | Completaciones únicas (constraint user+challenge) |
| `challenge_runs` | Sesiones activas con TTL |
| `remote_access_assignments` | Asignaciones Guacamole por sesión |
| `student_groups` | Grupos académicos con identificador Guacamole |
| `group_memberships` | Relación N:M usuario-grupo |
| `challenge_group_assignments` | Relación N:M reto-grupo |
| `laboratories` | Laboratorios virtuales por VLAN/subnet |
| `vm_assets` | VMs con IP, OS, perfil, ID Guacamole, ID Nutanix |
| `user_vm_connections` | Conexiones Guacamole individuales por jugador y VM |
| `audit_events` | Log inmutable de todas las operaciones administrativas |

---

## 10. Variables de Entorno

| Variable | Default (dev) | Producción |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@localhost/ctf_platform` | Ajustar host/credenciales |
| `REDIS_URL` | `redis://localhost:6379/0` | Ajustar host |
| `JWT_SECRET` | `unsafe-development-secret-change-me` | **Secreto aleatorio largo** |
| `FIELD_HMAC_SECRET` | `unsafe-development-hmac-change-me` | **Secreto aleatorio largo** |
| `ACCESS_TOKEN_MINUTES` | `20` | Ajustar según política |
| `CTF_SEED_DEMO_DATA` | `true` | `false` en producción limpia |
| `GUACAMOLE_MODE` | `stub` | `live` |
| `GUACAMOLE_API_URL` | *(vacío)* | URL interna del API de Guacamole |
| `GUACAMOLE_SERVICE_ACCOUNT` | *(vacío)* | Cuenta de servicio |
| `GUACAMOLE_SERVICE_PASSWORD` | *(vacío)* | Contraseña de servicio |
| `PUBLIC_ORIGIN` | `http://localhost:8081` | URL pública del servidor |
| `WEB_PORT` | `8081` | Puerto expuesto en el host |

---

## 11. Brecha con el MVP Objetivo

### Implementado ✅

- RBAC con 4 roles y dependencias FastAPI
- Autenticación JWT + Argon2id
- CRUD completo: retos, flags, usuarios, grupos, labs, VMs
- Flags estáticas y dinámicas con anti-sharing
- Ranking en tiempo real: WebSocket + Redis pub/sub
- Integración Apache Guacamole con Port & Adapter
- Rate limiting con degradación graceful
- Audit log completo e inmutable
- Reporte de progreso por grupo y exportación CSV
- Seed automático de roles, laboratorios y 17 retos demo

### Pendiente para MVP completo ⬜

- Refactoring hexagonal: extraer servicios de dominio del `main.py`
- Patrón Repository: `ChallengeRepository`, `UserRepository`, `SubmissionRepository`
- Patrón Strategy para validación de flags (campo `validator` ya existe en el modelo)
- Routers FastAPI separados por dominio
- Migraciones Alembic en lugar de `ALTER TABLE IF NOT EXISTS`
- Endpoint de refresh token (campo `REFRESH_TOKEN_DAYS` ya existe en Settings)
- Corrección: `_group_view()` definida dos veces en `main.py`
- Headers `Content-Security-Policy` en respuestas HTTP
