# Infraestructura y Despliegue
> **Fuente:** `docker-compose.yml`, `Dockerfile` (backend/frontend), `nginx.conf`, `.env.example` · **Generado:** 2026-09-17

---

## Tabla de Contenidos

1. [Visión general de la infraestructura](#1-visión-general-de-la-infraestructura)
2. [Servicios Docker Compose](#2-servicios-docker-compose)
3. [Red interna (ctf_internal)](#3-red-interna-ctf_internal)
4. [Volúmenes persistentes](#4-volúmenes-persistentes)
5. [Dockerfile: Backend (API)](#5-dockerfile-backend-api)
6. [Dockerfile: Frontend (Web)](#6-dockerfile-frontend-web)
7. [Configuración Nginx](#7-configuración-nginx)
8. [Variables de entorno](#8-variables-de-entorno)
9. [Flujo de inicio de los servicios](#9-flujo-de-inicio-de-los-servicios)
10. [Infraestructura objetivo: LAB-CTFWEB en Nutanix AHV](#10-infraestructura-objetivo-lab-ctfweb-en-nutanix-ahv)
11. [Guía de despliegue en Ubuntu (LAB-CTFWEB)](#11-guía-de-despliegue-en-ubuntu-lab-ctfweb)
12. [Relación con Apache Guacamole](#12-relación-con-apache-guacamole)
13. [Checklist de producción](#13-checklist-de-producción)

---

## 1. Visión General de la Infraestructura

`
Internet / LAN del laboratorio
         │
         ▼  :8081 (o :443 con TLS terminado externamente)
┌─────────────────────────────────────────────────┐
│              Docker Compose (ctf_internal)       │
│                                                 │
│  ┌──────────────────┐   proxy /api/             │
│  │  web (Nginx)     │──────────────────────►    │
│  │  nginx:1.27-alpine│                     │    │
│  │  Puerto 80 →     │   ◄────────────────  │    │
│  │  dist/ (React)   │                     │    │
│  └──────────────────┘                     │    │
│                                           │    │
│                          ┌────────────────┘    │
│                          ▼                      │
│  ┌──────────────────────────────┐               │
│  │  api (FastAPI + Uvicorn)     │               │
│  │  python:3.12-slim            │               │
│  │  Puerto interno 8000         │               │
│  │  Usuario: appuser (UID 10001)│               │
│  └──────┬───────────┬──────────┘               │
│         │           │                           │
│         ▼           ▼                           │
│  ┌────────────┐ ┌───────────┐                   │
│  │ postgres   │ │  redis    │                   │
│  │  16-alpine │ │  7-alpine │                   │
│  │  :5432     │ │  :6379    │                   │
│  └────────────┘ └───────────┘                   │
│         │                                       │
│  postgres_data (volume)                         │
│  redis_data    (volume)                         │
└─────────────────────────────────────────────────┘
         │
         │  HTTP REST (guacamole_mode=live)
         ▼
┌─────────────────────┐
│  Apache Guacamole   │  (servidor externo)
│  guacamole.lab      │
│  :8080 ó :443       │
└──────────┬──────────┘
           │ RDP / SSH / VNC
           ▼
┌────────────────────────────────┐
│  VMs en Nutanix AHV            │
│  VLAN 20: Atacantes (Kali)     │
│  VLAN 30: Víctimas (Win/Linux) │
└────────────────────────────────┘
`

---

## 2. Servicios Docker Compose

### Archivo completo: `docker-compose.yml`

`yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: 
      POSTGRES_USER: 
      POSTGRES_PASSWORD: 
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U POSTGRES_USER -d POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks: [ctf_internal]

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks: [ctf_internal]

  api:
    build: ./backend
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    expose:
      - "8000"
    networks: [ctf_internal]

  web:
    build: ./frontend
    depends_on:
      - api
    ports:
      - ":80"
    networks: [ctf_internal]

volumes:
  postgres_data:
  redis_data:

networks:
  ctf_internal:
    driver: bridge
`

---

### 2.1 Servicio: `postgres`

| Propiedad | Valor |
|---|---|
| **Imagen** | `postgres:16-alpine` |
| **Puerto** | 5432 (interno, no expuesto al host) |
| **Variables** | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| **Persistencia** | Volumen `postgres_data` → `/var/lib/postgresql/data` |
| **Health check** | `pg_isready -U  -d ` cada 5s, hasta 10 reintentos |
| **Red** | Exclusivamente `ctf_internal` |

**Comportamiento al inicio:**
- Crea la base de datos `ctf_platform` si no existe
- El servicio `api` espera a que el health check pase antes de arrancar

**Dependencia crítica:** El API no se inicia hasta que PostgreSQL reporta `healthy`. Esto evita errores de conexión durante el arranque.

---

### 2.2 Servicio: `redis`

| Propiedad | Valor |
|---|---|
| **Imagen** | `redis:7-alpine` |
| **Puerto** | 6379 (interno, no expuesto al host) |
| **Comando** | `redis-server --appendonly yes` (persistencia AOF activada) |
| **Persistencia** | Volumen `redis_data` → `/data` |
| **Health check** | `redis-cli ping` cada 5s, hasta 10 reintentos |
| **Red** | Exclusivamente `ctf_internal` |

**Usos en la plataforma:**

| Uso | Mecanismo | Detalle |
|---|---|---|
| Rate limiting login | `INCR` + `EXPIRE` | Clave `rate:login:{username}` → 10 req/60s |
| Rate limiting submit | `INCR` + `EXPIRE` | Clave `rate:flag:{uid}:{code}` → 8 req/60s |
| Rate limiting start | `INCR` + `EXPIRE` | Clave `rate:start:{uid}:{code}` → 6 req/60s |
| Pub/Sub ranking | `PUBLISH ctf:ranking` | Canal para futura distribución multi-instancia |

**AOF (Append-Only File):** Garantiza que las claves de rate limiting sobrevivan a un reinicio del contenedor Redis, evitando que un reinicio sea un vector para bypassear rate limits.

---

### 2.3 Servicio: `api`

| Propiedad | Valor |
|---|---|
| **Build** | `./backend` (Python 3.12-slim) |
| **Puerto** | 8000 (`expose`, solo accesible dentro de `ctf_internal`) |
| **Variables** | Cargadas desde `.env` vía `env_file` |
| **Dependencias** | `postgres` (healthy) + `redis` (healthy) |
| **Usuario** | `appuser` (UID 10001) — sin privilegios root |
| **Comando** | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers` |
| **Red** | Exclusivamente `ctf_internal` |

**`--proxy-headers`:** Uvicorn lee `X-Forwarded-For` y `X-Forwarded-Proto` del proxy Nginx para registrar IPs reales en el audit log y para que los WebSocket detecten correctamente el protocolo (ws/wss).

> El puerto 8000 **no se expone al host** (`expose` vs `ports`). Solo Nginx puede acceder al API desde dentro de `ctf_internal`.

---

### 2.4 Servicio: `web`

| Propiedad | Valor |
|---|---|
| **Build** | `./frontend` (Node 22 + Nginx 1.27-alpine) |
| **Puerto host** | `:80` (configurable) |
| **Dependencias** | `api` (sin health check; se inicia después) |
| **Red** | `ctf_internal` |
| **Contenido estático** | `dist/` de Vite copiado a `/usr/share/nginx/html` |

**El único puerto expuesto al exterior** del sistema es el de `web`. Todo el tráfico pasa por Nginx.

---

## 3. Red Interna (ctf_internal)

`yaml
networks:
  ctf_internal:
    driver: bridge
`

**Aislamiento:** Todos los servicios comparten la red virtual `ctf_internal`. Ningún servicio excepto `web` publica puertos al host.

**Resolución DNS interna:** Docker Compose asigna hostnames por nombre de servicio:

| Hostname interno | Servicio |
|---|---|
| `postgres` | Base de datos PostgreSQL |
| `redis` | Cache Redis |
| `api` | FastAPI (accedido por Nginx como `http://api:8000`) |
| `web` | Nginx (accedido externamente por el puerto publicado) |

**Ejemplo de configuración en `.env`:**
`
DATABASE_URL=postgresql+asyncpg://ctf_platform:PASSWORD@postgres:5432/ctf_platform
REDIS_URL=redis://redis:6379/0
`

---

## 4. Volúmenes Persistentes

`yaml
volumes:
  postgres_data:   # Named volume gestionado por Docker
  redis_data:      # Named volume gestionado por Docker
`

| Volumen | Montado en | Contenido |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Datos de BD: roles, usuarios, retos, submissions, audit log |
| `redis_data` | `/data` | AOF de Redis: estado de rate limiting |

**Ubicación en el host:** Docker los gestiona en `/var/lib/docker/volumes/` por defecto.

**Backup de datos:**
`ash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U ctf_platform ctf_platform > backup_.sql

# Restore PostgreSQL
docker compose exec -T postgres psql -U ctf_platform ctf_platform < backup_20260917.sql
`

---

## 5. Dockerfile: Backend (API)

`dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
`

**Análisis de capas:**

| Capa | Propósito |
|---|---|
| `FROM python:3.12-slim` | Imagen base mínima sin herramientas de compilación innecesarias |
| `ENV PYTHONDONTWRITEBYTECODE=1` | Evita generar archivos `.pyc` en el contenedor |
| `ENV PYTHONUNBUFFERED=1` | Los logs de Python se envían inmediatamente a stdout/stderr (visibles con `docker logs`) |
| `COPY requirements.txt .` + `pip install` | Capa separada: se cachea si `requirements.txt` no cambia |
| `COPY app ./app` | El código de la aplicación en su propia capa |
| `useradd --uid 10001 appuser` | Principio de mínimo privilegio: el proceso no corre como root |
| `CMD uvicorn ... --proxy-headers` | Lee cabeceras de proxy para IPs y protocolo reales |

---

## 6. Dockerfile: Frontend (Web)

`dockerfile
# Etapa 1: Build
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Etapa 2: Producción
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
`

**Multi-stage build:**

| Etapa | Base | Resultado |
|---|---|---|
| `build` | `node:22-alpine` | Ejecuta `tsc -b && vite build` → genera `dist/` |
| Producción | `nginx:1.27-alpine` | Solo contiene Nginx + archivos estáticos (~15 MB) |

El artefacto final **no incluye Node.js** ni las herramientas de desarrollo. El tamaño de la imagen de producción es mínimo.

---

## 7. Configuración Nginx

`
ginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Headers de seguridad HTTP
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Proxy reverso hacia el API (HTTP + WebSocket)
    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade ;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host System.Management.Automation.Internal.Host.InternalHost;
        proxy_set_header X-Forwarded-Proto ;
        proxy_set_header X-Forwarded-For ;
    }

    # SPA: todas las rutas no encontradas sirven index.html
    location / {
        try_files  / /index.html;
    }
}
`

**Headers de seguridad implementados:**

| Header | Valor | Protección |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Evita que el navegador interprete tipos MIME incorrectos |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limita información de referrer enviada a sitios externos |
| `X-Frame-Options` | `SAMEORIGIN` | Previene clickjacking en iframes externos |

**Headers pendientes (para MVP completo):**

| Header | Valor recomendado | Razón |
|---|---|---|
| `Content-Security-Policy` | `default-src 'self'; connect-src 'self' ws: wss:` | Crítico en plataforma CTF que muestra payloads de ataque |
| `Strict-Transport-Security` | `max-age=31536000` | Requiere TLS en el host externo |

**Soporte WebSocket:** Las directivas `Upgrade` y `Connection: "upgrade"` son esenciales para que los WebSockets (`/api/v1/ws/ranking`) atraviesen el proxy correctamente.

**Routing SPA:** `try_files  / /index.html` permite que el navegador navegue a cualquier ruta sin obtener 404 desde Nginx — React gestiona el routing internamente.

---

## 8. Variables de Entorno

Archivo de referencia: `.env.example` (copiar a `.env` y completar)

`ini
# Puerto expuesto al host para la interfaz web
WEB_PORT=8081

# PostgreSQL
POSTGRES_DB=ctf_platform
POSTGRES_USER=ctf_platform
POSTGRES_PASSWORD=CHANGE_ME_DB_PASSWORD

# FastAPI — conexión a PostgreSQL (host = nombre del servicio Docker)
DATABASE_URL=postgresql+asyncpg://ctf_platform:CHANGE_ME_DB_PASSWORD@postgres:5432/ctf_platform

# FastAPI — conexión a Redis (host = nombre del servicio Docker)
REDIS_URL=redis://redis:6379/0

# Seguridad: DEBEN ser cadenas aleatorias largas en producción
JWT_SECRET=CHANGE_ME_LONG_RANDOM_JWT_SECRET
FIELD_HMAC_SECRET=CHANGE_ME_LONG_RANDOM_HMAC_SECRET

# JWT
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=20
REFRESH_TOKEN_DAYS=7

# Datos de demostración
CTF_DEMO_PASSWORD=LabDemo-ChangeMe-2026!
CTF_SEED_DEMO_DATA=true

# Guacamole: "stub" para desarrollo, "live" para producción
GUACAMOLE_MODE=stub
GUACAMOLE_BASE_URL=http://guacamole.lab
GUACAMOLE_API_URL=
GUACAMOLE_SERVICE_ACCOUNT=
GUACAMOLE_SERVICE_PASSWORD=

# CORS: URL pública del servidor web
PUBLIC_ORIGIN=http://localhost:8081
`

**Generación de secretos seguros:**
`ash
# JWT_SECRET y FIELD_HMAC_SECRET deben ser únicos y diferentes
openssl rand -hex 32   # → 64 caracteres hexadecimales
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
`

---

## 9. Flujo de Inicio de los Servicios

`
docker compose up -d
       │
       ├─ postgres → healthcheck (pg_isready) ──────────────────────────────┐
       │                                                                     │
       ├─ redis → healthcheck (redis-cli ping) ─────────────────────────────┤
       │                                                                     │
       │              ┌─── postgres: healthy ───┐                           │
       │              │    redis: healthy    ────┤                           │
       │              ▼                          ▼                           │
       ├─ api ──► uvicorn arranca                                            │
       │              │                                                      │
       │              ├─ lifespan.startup                                    │
       │              │     ├─ create_schema() → CREATE TABLE IF NOT EXISTS  │
       │              │     ├─ seed_data()    → Roles + Labs + 17 retos      │
       │              │     ├─ Redis pool     → conectado                    │
       │              │     └─ Guacamole      → stub o live adapter          │
       │              │                                                      │
       │              └─ FastAPI listo en :8000 ◄──────────────────────────┘
       │
       └─ web (Nginx) → sirve dist/ en :80 (expuesto como WEB_PORT:80)
              │
              └─ Proxy /api/ → http://api:8000
`

**Health check cascade:** El orden `postgres → redis → api → web` garantiza que cada servicio solo arranque cuando sus dependencias están listas. Sin health checks, Uvicorn podría intentar conectarse a PostgreSQL antes de que esté disponible.

---

## 10. Infraestructura Objetivo: LAB-CTFWEB en Nutanix AHV

La plataforma se despliega en una VM dedicada dentro del clúster Nutanix AHV:

`
Clúster Nutanix AHV
├── LAB-CTFWEB (Ubuntu Server 26.04)     ← Plataforma CTF (este proyecto)
│     └── Docker Compose
│           ├── postgres (VLAN interna)
│           ├── redis    (VLAN interna)
│           ├── api      (VLAN interna)
│           └── web      → puerto 8081 expuesto
│
├── Guacamole Server (VM separada o servicio)
│     └── API REST + guacd + MySQL/PostgreSQL
│
├── VLAN 20: Atacantes
│     ├── LAB-KALI       (10.10.20.10)
│     ├── LAB-KALI-PURPLE (10.10.20.11)
│     └── LAB-KALI-BLUE  (10.10.20.12)
│
└── VLAN 30: Víctimas
      ├── LAB-WINVICT-A  (10.10.30.10)
      ├── LAB-WINVICT-B  (10.10.30.11)
      ├── LAB-LNXVICT    (192.168.146.137)
      ├── LAB-SRVWEB     (10.10.30.20)
      └── LAB-SRVFSAD    (10.10.30.21)
`

**Configuración de red recomendada para LAB-CTFWEB:**

| Interfaz | VLAN | Propósito |
|---|---|---|
| eth0 | Management (VLAN de administración) | Acceso SSH al servidor, exposición del puerto 8081 |
| eth1 (opcional) | VLAN 20/30 | Comunicación directa con VMs si Guacamole está en la misma VM |

---

## 11. Guía de Despliegue en Ubuntu (LAB-CTFWEB)

### Prerrequisitos del servidor

`ash
# 1. Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Docker Engine
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker 
newgrp docker

# 3. Docker Compose (incluido en Docker Engine >=23)
docker compose version
`

### Despliegue inicial

`ash
# 1. Clonar o copiar el repositorio
git clone <repo-url> /opt/ctf-platform
cd /opt/ctf-platform

# 2. Configurar variables de entorno
cp .env.example .env
nano .env  # Completar POSTGRES_PASSWORD, JWT_SECRET, FIELD_HMAC_SECRET,
           # GUACAMOLE_MODE, GUACAMOLE_API_URL, GUACAMOLE_SERVICE_ACCOUNT, etc.

# 3. Construir imágenes
docker compose build

# 4. Iniciar todos los servicios
docker compose up -d

# 5. Verificar estado
docker compose ps
docker compose logs api --tail=50
`

### Verificación del despliegue

`ash
# Health check del API
curl http://localhost:8081/api/v1/health
# Esperado: {"status":"ok","service":"ctf-api"}

# Verificar base de datos (tablas creadas)
docker compose exec postgres psql -U ctf_platform -c "\dt"

# Verificar Redis
docker compose exec redis redis-cli ping
# Esperado: PONG
`

### Actualización sin tiempo de inactividad

`ash
# 1. Obtener nuevos cambios
git pull

# 2. Reconstruir solo las imágenes que cambiaron
docker compose build api web

# 3. Recrear contenedores con las nuevas imágenes
docker compose up -d --no-deps api web

# Los volúmenes postgres_data y redis_data se conservan
`

### Comandos útiles de operación

`ash
# Ver logs en tiempo real
docker compose logs -f api

# Reiniciar solo el API (sin tocar BD)
docker compose restart api

# Backup completo de la BD
docker compose exec postgres pg_dump -U ctf_platform ctf_platform \
  | gzip > /backups/ctf_.sql.gz

# Abrir consola PostgreSQL
docker compose exec postgres psql -U ctf_platform

# Abrir consola Redis
docker compose exec redis redis-cli

# Monitorear recursos de contenedores
docker stats
`

---

## 12. Relación con Apache Guacamole

### Modos de operación

| Modo | `GUACAMOLE_MODE` | Uso |
|---|---|---|
| **Stub** | `stub` | Desarrollo/CI: el adaptador retorna respuestas ficticias sin llamadas HTTP reales |
| **Live** | `live` | Producción: el adaptador llama a la API REST de Guacamole con autenticación real |

### Configuración para modo live

`ini
# .env
GUACAMOLE_MODE=live
GUACAMOLE_BASE_URL=http://guacamole.lab:8080   # URL pública para los links de usuario
GUACAMOLE_API_URL=http://guacamole.lab:8080    # URL interna del API REST
GUACAMOLE_SERVICE_ACCOUNT=ctf-service          # Usuario con permisos ADMINISTER
GUACAMOLE_SERVICE_PASSWORD=SecurePassword123!  # Contraseña del servicio
`

### Flujo de autenticación con Guacamole (modo live)

`
api → POST http://guacamole.lab:8080/api/tokens
      Form: username=ctf-service&password=...
      Response: { "authToken": "...", "dataSource": "mysql" }

      Token usado como ?token=<authToken>&datasource=mysql
      en todas las llamadas subsiguientes
`

### Operaciones del adaptador Live

| Operación | Endpoint Guacamole |
|---|---|
| Listar usuarios | `GET /api/session/data/{ds}/users` |
| Crear usuario | `POST /api/session/data/{ds}/users` |
| Actualizar usuario | `PUT /api/session/data/{ds}/users/{user}` |
| Eliminar usuario | `DELETE /api/session/data/{ds}/users/{user}` |
| Listar conexiones | `GET /api/session/data/{ds}/connections` |
| Crear conexión | `POST /api/session/data/{ds}/connections` |
| Clonar conexión | Lee parámetros de `GET /api/session/data/{ds}/connections/{id}/parameters` y crea nueva con `POST` |
| Permisos usuario | `PATCH /api/session/data/{ds}/users/{user}/permissions` |
| Crear user group | `POST /api/session/data/{ds}/userGroups` |
| Agregar a group | `PATCH /api/session/data/{ds}/userGroups/{id}/memberUsers` |

---

## 13. Checklist de Producción

### Seguridad crítica

- [ ] `POSTGRES_PASSWORD` cambiado a una cadena aleatoria segura (≥32 chars)
- [ ] `JWT_SECRET` cambiado a una cadena aleatoria única (≥64 chars, `openssl rand -hex 32`)
- [ ] `FIELD_HMAC_SECRET` cambiado a una cadena aleatoria única diferente del JWT_SECRET
- [ ] `CTF_SEED_DEMO_DATA=false` si se despliega en entorno limpio (o `true` para datos de demo)
- [ ] `GUACAMOLE_MODE=live` y credenciales de servicio configuradas
- [ ] `PUBLIC_ORIGIN` apunta a la URL real del servidor (e.g., `http://192.168.X.X:8081`)
- [ ] Firewall del host: solo exponer el puerto `WEB_PORT` (8081) al exterior

### Seguridad recomendada (mejoras)

- [ ] Proxy TLS (Nginx externo o Caddy) terminando HTTPS en puerto 443 antes del contenedor `web`
- [ ] Añadir `Content-Security-Policy` header en `nginx.conf`
- [ ] Añadir `Strict-Transport-Security` si se usa HTTPS
- [ ] Deshabilitar root login SSH en LAB-CTFWEB
- [ ] Acceso SSH al servidor solo por clave pública (deshabilitar password auth)

### Operaciones

- [ ] Backup automático de `postgres_data` programado (cron diario)
- [ ] Logs de `api` redirigidos a sistema de logging centralizado o rotados con `logrotate`
- [ ] Monitoreo de recursos (CPU, RAM, disco) del contenedor en ejecución
- [ ] Probar restauración del backup antes de producción

### Guacamole

- [ ] Cuenta de servicio `GUACAMOLE_SERVICE_ACCOUNT` creada con permiso `ADMINISTER`
- [ ] URL de Guacamole accesible desde el contenedor `api` (DNS o IP directa)
- [ ] Conexiones de plantilla creadas en Guacamole (SSH/RDP/VNC) para clonar por estudiante
- [ ] VMs en Nutanix con `guacamole_connection_id` registrados en la BD via panel admin
