# 🚀 Guía de Ejecución Local — CTF Platform

Guía paso a paso para clonar, configurar y ejecutar la plataforma CTF completamente en tu máquina local usando Docker Compose.

---

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Clonar el repositorio](#2-clonar-el-repositorio)
3. [Configurar variables de entorno](#3-configurar-variables-de-entorno)
4. [Levantar los servicios con Docker Compose](#4-levantar-los-servicios-con-docker-compose)
5. [Verificar que todo esté en funcionamiento](#5-verificar-que-todo-esté-en-funcionamiento)
6. [Acceder a la plataforma](#6-acceder-a-la-plataforma)
7. [Detener los servicios](#7-detener-los-servicios)
8. [Desarrollo sin Docker (opcional)](#8-desarrollo-sin-docker-opcional)
9. [Solución de problemas](#9-solución-de-problemas)
10. [Checklist rápido](#10-checklist-rápido)

---

## 1. Requisitos previos

Antes de comenzar, asegúrate de tener instaladas las siguientes herramientas:

| Herramienta | Versión mínima | Cómo verificar |
|---|---|---|
| **Git** | Cualquier versión estable | `git --version` |
| **Docker Desktop** | Versión estable actual | `docker --version` |
| **Docker Compose** | Incluido con Docker Desktop | `docker compose version` |

> [!IMPORTANT]
> En **Windows**, Docker Desktop debe estar **iniciado** antes de ejecutar cualquier comando de Compose. Asegúrate de ver el ícono de Docker corriendo en la bandeja del sistema.

> [!NOTE]
> **Python 3.12** y **Node.js 22** solo son necesarios si quieres ejecutar el backend o el frontend directamente en el host (fuera de Docker). Para la ejecución estándar con Compose, **no son requeridos**.

---

## 2. Clonar el repositorio

Abre una terminal (PowerShell, Windows Terminal o WSL) y clona el repositorio:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd ctf-platform
```

Verifica que el remoto esté configurado correctamente:

```powershell
git remote -v
```

---

## 3. Configurar variables de entorno

Este es el paso más importante antes de levantar los servicios.

### 3.1 Copiar la plantilla

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

### 3.2 Editar el archivo `.env`

Abre `.env` con tu editor favorito y **reemplaza todos los valores `CHANGE_ME`**:

```dotenv
# Puerto de acceso al frontend (puedes dejarlo en 8081)
WEB_PORT=8081

# Base de datos PostgreSQL
POSTGRES_DB=ctf_platform
POSTGRES_USER=ctf_platform
POSTGRES_PASSWORD=UnaContraseñaSegura123   # ← CAMBIA ESTO

# URL de conexión interna (reemplaza la contraseña aquí también)
DATABASE_URL=postgresql+asyncpg://ctf_platform:UnaContraseñaSegura123@postgres:5432/ctf_platform

# Redis (puedes dejarlo como está para uso local)
REDIS_URL=redis://redis:6379/0

# Secretos JWT y HMAC — usa cadenas largas y aleatorias
JWT_SECRET=una-cadena-muy-larga-y-aleatoria-aqui     # ← CAMBIA ESTO
FIELD_HMAC_SECRET=otra-cadena-muy-larga-y-aleatoria  # ← CAMBIA ESTO

# Configuración de tokens
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=20
REFRESH_TOKEN_DAYS=7

# Datos demo (usuario de prueba)
CTF_DEMO_PASSWORD=LabDemo-ChangeMe-2026!
CTF_SEED_DEMO_DATA=true

# Guacamole (modo stub para desarrollo local sin laboratorio real)
GUACAMOLE_MODE=stub
PUBLIC_ORIGIN=http://localhost:8081

# Inyector de flags (deshabilitado por defecto en desarrollo)
FLAG_INJECTOR_ENABLED=false
```

> [!CAUTION]
> **Nunca** subas el archivo `.env` a GitHub. Ya está excluido en `.gitignore`, pero verifica siempre con `git status` antes de hacer `git add .`.

---

## 4. Levantar los servicios con Docker Compose

Desde la **raíz del repositorio** (donde está el archivo `docker-compose.yml`), ejecuta:

### 4.1 Primera vez (o cuando cambies código/dependencias)

```powershell
docker compose up --build -d
```

Este comando:
1. Construye la imagen del **backend** (FastAPI + Python 3.12).
2. Construye la imagen del **frontend** (React + Vite + Nginx).
3. Descarga las imágenes de **PostgreSQL 16** y **Redis 7**.
4. Inicia todos los contenedores en segundo plano (`-d`).
5. El backend inicializa automáticamente el esquema de la base de datos al arrancar.

> [!NOTE]
> La primera vez puede tardar varios minutos mientras se descargan las imágenes base y se instalan las dependencias.

### 4.2 Veces siguientes (sin cambios en código)

```powershell
docker compose up -d
```

---

## 5. Verificar que todo esté en funcionamiento

### 5.1 Ver el estado de los contenedores

```powershell
docker compose ps
```

Deberías ver **4 servicios** con estado `running` (o `healthy`):

```
NAME                STATUS          PORTS
ctf-platform-postgres-1   running (healthy)
ctf-platform-redis-1      running (healthy)
ctf-platform-api-1        running
ctf-platform-web-1        running          0.0.0.0:8081->80/tcp
```

### 5.2 Ver logs en tiempo real

```powershell
# Todos los servicios
docker compose logs -f

# Solo el backend (API)
docker compose logs -f api

# Solo la base de datos
docker compose logs -f postgres

# Solo Redis
docker compose logs -f redis
```

Presiona `Ctrl+C` para salir de los logs sin detener los servicios.

> [!TIP]
> Si el servicio `api` muestra errores al arrancar, revisa primero si `postgres` ya está `healthy`. El backend espera a que la base de datos esté lista antes de iniciar.

---

## 6. Acceder a la plataforma

Una vez que todos los servicios estén en estado `running`, abre tu navegador:

| Servicio | URL |
|---|---|
| **Frontend (plataforma CTF)** | [http://localhost:8081](http://localhost:8081) |
| **API Backend (interno)** | `http://localhost:8000` (solo accesible desde la red interna de Docker) |

> [!NOTE]
> Si cambiaste `WEB_PORT` en tu `.env`, usa ese puerto en lugar de `8081`.

### Credenciales de demo (si `CTF_SEED_DEMO_DATA=true`)

Al arrancar por primera vez, el backend crea un usuario demo. La contraseña es la que configuraste en `CTF_DEMO_PASSWORD` dentro de tu `.env`.

---

## 7. Detener los servicios

### Detener sin borrar datos

```powershell
docker compose down
```

Esto detiene y elimina los contenedores, pero **conserva los volúmenes** (`postgres_data`, `redis_data`). La próxima vez que hagas `docker compose up`, los datos persisten.

### Detener y eliminar todos los datos (⚠️ destructivo)

```powershell
docker compose down -v
```

> [!CAUTION]
> El flag `-v` **elimina los volúmenes** de PostgreSQL y Redis. Todos los datos del entorno local se perderán. Úsalo solo si quieres empezar completamente desde cero.

---

## 8. Desarrollo sin Docker (opcional)

Solo sigue estos pasos si necesitas ejecutar el backend o frontend directamente en tu máquina para desarrollo con hot-reload avanzado.

### 8.1 Backend (FastAPI)

> [!IMPORTANT]
> Para esto necesitas PostgreSQL y Redis corriendo. Puedes levantarlos con Compose sin el resto: `docker compose up -d postgres redis`.

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Linux / macOS:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API quedará disponible en `http://localhost:8000` y la documentación Swagger en `http://localhost:8000/docs`.

### 8.2 Frontend (React + Vite)

```powershell
cd frontend
npm ci
npm run dev
```

El servidor de desarrollo de Vite arrancará normalmente en `http://localhost:5173`.

---

## 9. Solución de problemas

| Problema | Posible causa | Solución |
|---|---|---|
| `docker compose` no se reconoce | Compose no instalado o Docker no iniciado | Iniciar Docker Desktop y verificar con `docker compose version` |
| No abre `http://localhost:8081` | El contenedor `web` no está activo o el puerto está ocupado | Ejecutar `docker compose ps` y revisar logs con `docker compose logs web` |
| El backend falla al iniciar | `POSTGRES_PASSWORD` vacía o `DATABASE_URL` incorrecta | Revisar el archivo `.env` y que `CHANGE_ME` fue reemplazado |
| Error de conexión a PostgreSQL | `postgres` no está saludable aún | Esperar a que el healthcheck pase: `docker compose ps` |
| Error de conexión a Redis | `REDIS_URL` incorrecta | Verificar que `redis` esté `healthy` y que la URL coincida |
| Cambios en el código no aparecen | La imagen no fue reconstruida | Ejecutar `docker compose up --build` |
| Error `POSTGRES_PASSWORD: Configure POSTGRES_PASSWORD in .env` | El `.env` no existe o la variable está vacía | Asegúrate de haber copiado `.env.example` a `.env` y editado la contraseña |
| Falla `pip install` | Entorno virtual incorrecto o problema de red | Verificar que el `.venv` esté activado y `python --version` sea 3.12 |
| Falla `npm ci` | Versión de Node incompatible | Usar Node.js 22 y ejecutar desde el directorio `frontend/` |

---

## 10. Checklist rápido

Usa esta lista para verificar que tu entorno esté listo:

- [ ] Docker Desktop instalado y **corriendo**
- [ ] Git instalado
- [ ] Repositorio clonado
- [ ] Archivo `.env` creado a partir de `.env.example`
- [ ] Todos los `CHANGE_ME` reemplazados en `.env`
- [ ] `docker compose up --build -d` ejecutado sin errores
- [ ] Los 4 servicios aparecen como `running` en `docker compose ps`
- [ ] `postgres` y `redis` aparecen como `(healthy)`
- [ ] La plataforma es accesible en `http://localhost:8081`

---

*Generado el 2026-10-05 · Basado en la estructura real del repositorio `ctf-platform`.*
