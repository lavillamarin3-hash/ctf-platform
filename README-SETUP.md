# Guía de instalación y desarrollo

Guía para preparar una estación de trabajo, ejecutar la plataforma CTF y
colaborar mediante Git y GitHub.

> **Alcance de esta guía:** refleja la implementación actual del repositorio.
> Cuando una capacidad aparece en la arquitectura, pero todavía no está
> configurada en los archivos del proyecto, se indica explícitamente como
> pendiente.

## 1. Requisitos previos

### Herramientas necesarias en el host

| Herramienta | Versión recomendada | Propósito |
| --- | --- | --- |
| Git | Versión estable actual | Control de versiones y colaboración |
| Cuenta de GitHub | Cuenta con acceso al repositorio | Repositorio remoto y Pull Requests |
| Docker | Versión estable actual | Construcción y ejecución de contenedores |
| Docker Compose | `docker compose` incluido en Docker Desktop/Engine | Orquestación local |
| Python | 3.12, si se ejecuta el backend fuera de Docker | Desarrollo directo del backend |
| Node.js | 22, si se ejecuta el frontend fuera de Docker | Desarrollo directo del frontend |
| npm | Incluido con Node.js | Instalación y scripts del frontend |

Docker es la ruta recomendada para ejecutar el sistema completo. PostgreSQL y
Redis se administran mediante Docker Compose y no necesitan instalarse
directamente en Windows, Linux o macOS.

### Dependencias administradas por Docker

El archivo [`docker-compose.yml`](./docker-compose.yml) define estos servicios:

- `postgres`: PostgreSQL 16 Alpine.
- `redis`: Redis 7 Alpine.
- `api`: backend FastAPI.
- `web`: frontend compilado y servido mediante Nginx.

## 2. Requisitos de hardware

### Requisitos mínimos sugeridos

No existen requisitos oficiales de hardware definidos en el repositorio. Para
desarrollo local se recomienda una estación con:

- Procesador de 4 núcleos o equivalente.
- 8 GB de RAM como mínimo sugerido; 16 GB facilita ejecutar Docker y las
  herramientas de desarrollo simultáneamente.
- Al menos 10 GB libres para imágenes, dependencias y volúmenes locales.
- Conectividad de red para descargar imágenes y dependencias.

Estas cifras son recomendaciones de desarrollo, no requisitos oficiales del
proyecto.

## 3. Sistemas operativos compatibles

### Windows 11

1. Instalar Docker Desktop con integración WSL 2 habilitada.
2. Instalar Git para Windows.
3. Usar PowerShell, Windows Terminal o una terminal WSL.
4. Clonar el repositorio en una carpeta de trabajo local.
5. Ejecutar Docker Compose desde la raíz del repositorio.

### Linux

1. Instalar Git.
2. Instalar Docker Engine y el complemento Docker Compose según la distribución.
3. Verificar que el usuario tenga permisos para ejecutar Docker.
4. Clonar el repositorio y ejecutar los comandos desde su raíz.

### macOS

1. Instalar Docker Desktop.
2. Instalar Git (por Xcode Command Line Tools o el instalador disponible).
3. Clonar el repositorio y ejecutar los comandos desde su raíz.

Los comandos Docker Compose de esta guía utilizan la sintaxis actual
`docker compose`, no el binario antiguo `docker-compose`.

## 4. Instalación de herramientas

### Git

Verificar la instalación:

```powershell
git --version
```

### Docker

Verificar Docker y Docker Compose:

```powershell
docker --version
docker compose version
```

En Windows, Docker Desktop debe estar iniciado antes de ejecutar Compose.

### Python

El backend se construye actualmente sobre la imagen `python:3.12-slim`.
Verificar Python si se va a ejecutar fuera de Docker:

```powershell
python --version
```

En Linux o macOS puede ser necesario utilizar:

```bash
python3 --version
```

### Node.js y npm

El frontend se construye actualmente sobre `node:22-alpine`. Verificar:

```powershell
node --version
npm --version
```

## 5. Configuración de Git

Configurar la identidad del desarrollador usando los valores propios:

```powershell
git config --global user.name "Nombre Apellido"
git config --global user.email "correo@example.com"
```

Verificar la configuración:

```powershell
git config --global --list
```

No almacenar contraseñas, tokens ni claves privadas en la configuración del
repositorio.

## 6. Autenticación con GitHub

Se recomienda utilizar SSH o GitHub CLI con autenticación interactiva. No
compartir credenciales ni introducir contraseñas en scripts.

### Opción recomendada: GitHub CLI

Si GitHub CLI está instalado:

```powershell
gh auth login
gh auth status
```

Seguir el asistente oficial y seleccionar el método de autenticación disponible
para la organización.

### Opción SSH

1. Crear una clave SSH en el equipo, si no existe.
2. Agregar la clave pública a la configuración de GitHub.
3. Iniciar el agente SSH y cargar la clave según el sistema operativo.
4. Probar la conexión:

```powershell
ssh -T git@github.com
```

La clave privada debe permanecer únicamente en el equipo del desarrollador.

### Opción HTTPS

Puede utilizarse HTTPS junto con Git Credential Manager. No pegar contraseñas
ni tokens directamente en comandos o archivos versionados.

## 7. Clonar el repositorio

La URL real del repositorio no está definida en los archivos disponibles.
Sustituir los placeholders por la URL proporcionada por el equipo:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_REPOSITORIO>
```

Verificar el remoto:

```powershell
git remote -v
```

## 8. Estructura del repositorio

La estructura actualmente disponible es:

```text
ctf_project/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── package-lock.json
│   └── src/
├── .env.example
├── docker-compose.yml
└── README.md
```

El backend utiliza `backend/app/` como paquete de aplicación. El frontend
utiliza `frontend/src/`.

La separación conceptual de Arquitectura Hexagonal es:

- **Domain:** reglas y entidades del dominio.
- **Application:** casos de uso.
- **Ports:** contratos de entrada y salida.
- **Adapters:** HTTP, persistencia, tiempo real y servicios externos.
- **Infrastructure:** implementaciones concretas.
- **API:** exposición de casos de uso a clientes.

No se deben asumir directorios con esos nombres: la estructura hexagonal
completa queda pendiente de reflejarse en carpetas explícitas si la
implementación las incorpora.

## 9. Variables de entorno

Copiar la plantilla local:

```powershell
Copy-Item .env.example .env
```

En Linux/macOS:

```bash
cp .env.example .env
```

Editar `.env` y cambiar los valores marcados como `CHANGE_ME`. La plantilla
actual contiene configuración para PostgreSQL, Redis, JWT, HMAC, datos demo,
Guacamole y el origen público de la aplicación.

Ejemplo conceptual, sin valores reales:

```dotenv
DATABASE_URL=...
REDIS_URL=...
JWT_SECRET=...
```

Nunca subir a GitHub:

- Contraseñas.
- Secretos JWT o HMAC.
- Tokens.
- Claves privadas.
- Credenciales de servicios.

El repositorio actual contiene `.env.example`, pero no contiene un archivo
`.gitignore` en la instantánea disponible. Antes de publicar cambios, el equipo
debe añadir y mantener un `.gitignore` que excluya al menos los archivos
indicados en la sección [Archivos que no deben subirse](#26-archivos-que-no-deben-subirse-a-github).

## 10. Dependencias Backend

El backend tiene un [`requirements.txt`](./backend/requirements.txt). Para
ejecutarlo directamente en el host:

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

La imagen de Docker instala estas dependencias automáticamente. No es
necesario crear el entorno virtual para la ejecución con Compose.

## 11. Dependencias Frontend

El frontend contiene `package.json` y `package-lock.json`.

Para instalar de forma reproducible:

```powershell
cd frontend
npm ci
```

Usar `npm install` cuando sea necesario actualizar el lockfile de forma
intencional:

```powershell
npm install
```

El script disponible para compilar es:

```powershell
npm run build
```

El contenedor frontend ejecuta `npm install` y después `npm run build`.

## 12. PostgreSQL y Redis

La ejecución preferida es Docker Compose desde la raíz del repositorio:

```powershell
docker compose up -d
```

Consultar el estado:

```powershell
docker compose ps
```

Consultar logs:

```powershell
docker compose logs
```

También puede consultarse un servicio concreto:

```powershell
docker compose logs api
docker compose logs postgres
docker compose logs redis
```

No se deben iniciar PostgreSQL o Redis manualmente en el host salvo que el
equipo defina una configuración alternativa compatible.

## 13. Migraciones de base de datos

Aunque Alembic forma parte de la arquitectura objetivo, no hay configuración
de Alembic ni archivo de migraciones en el repositorio actual. Por tanto:

> **Pendiente de configuración:** no ejecutar `alembic upgrade head` como paso
> del proyecto actual.

Durante el arranque, el backend crea el esquema mediante SQLAlchemy y aplica
ajustes de compatibilidad sobre volúmenes existentes desde
[`backend/app/db.py`](./backend/app/db.py).

## 14. Ejecución del backend

El comando real definido por [`backend/Dockerfile`](./backend/Dockerfile) es:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

Para ejecutarlo directamente después de activar el entorno virtual:

```powershell
cd backend
uvicorn app.main:app --reload
```

El puerto `8000` es el puerto interno del contenedor API. Compose lo expone al
servicio `web` mediante la red interna, pero no publica `8000` directamente en
el host.

FastAPI habilita la documentación OpenAPI/Swagger en `/docs` dentro del
servicio API. El proxy Nginx actual solo publica `/api/` hacia el backend; por
eso, el acceso externo directo a `/docs` queda **pendiente de configuración**
si no se ejecuta el backend directamente.

## 15. Ejecución del frontend

El script real definido en [`frontend/package.json`](./frontend/package.json)
es:

```powershell
cd frontend
npm run dev
```

Para compilar el frontend:

```powershell
npm run build
```

El Dockerfile del frontend compila la aplicación y sirve el resultado con
Nginx. El puerto publicado por Compose para esta interfaz es `8081` por
defecto.

## 16. Ejecución completa con Docker Compose

Desde la raíz del repositorio:

```powershell
docker compose up -d
docker compose ps
```

Para reconstruir las imágenes después de cambiar código o dependencias:

```powershell
docker compose up --build
```

Abrir:

```text
http://localhost:8081
```

El puerto puede cambiarse mediante `WEB_PORT` en `.env`.

Detener los servicios sin borrar volúmenes:

```powershell
docker compose down
```

## 17. Desarrollo diario

Flujo recomendado:

```text
Actualizar → Crear rama → Modificar → Probar → Commit → Push → Pull Request
```

Ejemplo:

```powershell
git checkout main
git pull
git checkout -b feature/nombre-de-la-funcionalidad
```

Después de trabajar:

```powershell
git status
git add .
git commit -m "feat: descripcion del cambio"
git push -u origin feature/nombre-de-la-funcionalidad
```

Revisar siempre `git status` antes de agregar archivos para no incluir `.env`,
secretos o artefactos generados.

## 18. Convención de ramas

Usar el nombre de la rama principal que exista realmente en GitHub. En esta
instantánea no se define una rama `develop`, por lo que no debe asumirse su uso.

Convenciones sugeridas:

- `main`: rama principal.
- `feature/...`: funcionalidad nueva.
- `fix/...`: corrección.
- `docs/...`: documentación.
- `refactor/...`: reorganización sin cambio funcional intencional.
- `test/...`: pruebas.

## 19. Convención de commits

Se recomienda Conventional Commits:

```text
feat:
fix:
docs:
refactor:
test:
chore:
build:
ci:
```

Ejemplos:

```text
feat: agregar validacion de flags
fix: corregir actualizacion del ranking
docs: actualizar guia de instalacion
refactor: separar servicio de retos
test: agregar pruebas para validacion de flags
```

## 20. Pull Request

1. Crear una rama desde la rama base actualizada.
2. Realizar los cambios.
3. Ejecutar las verificaciones disponibles.
4. Crear un commit claro.
5. Subir la rama:

   ```powershell
   git push -u origin <NOMBRE_DE_LA_RAMA>
   ```

6. Abrir un Pull Request en GitHub.
7. Describir el objetivo, los cambios y las verificaciones realizadas.
8. Solicitar revisión.
9. Resolver comentarios y actualizar la misma rama.
10. Integrar el cambio según las reglas del repositorio.

## 21. Actualizar el repositorio local

Para actualizar la rama principal:

```powershell
git checkout main
git pull
```

Antes de actualizar una rama con trabajo local, guardar o confirmar los cambios
para evitar conflictos. Si el equipo adopta una rama `develop`, documentar ese
flujo cuando esté configurado oficialmente.

## 22. Resolución de conflictos

1. Identificar el estado:

   ```powershell
   git status
   ```

2. Abrir los archivos marcados y resolver manualmente las secciones en
   conflicto.
3. Revisar el resultado y agregar únicamente los archivos resueltos:

   ```powershell
   git add <archivo-resuelto>
   ```

4. Finalizar según la operación en curso:

   ```powershell
   git commit
   ```

   o, si se estaba realizando un rebase:

   ```powershell
   git rebase --continue
   ```

No usar comandos destructivos para descartar trabajo sin confirmar primero qué
archivos se verán afectados. Si hay dudas, detenerse y pedir revisión al
responsable de la rama.

## 23. Pruebas

No se encontraron suites ni scripts de pruebas automatizadas en la
implementación actual.

> **Pendiente de implementación:** pruebas unitarias, de integración, backend y
> frontend.

Mientras no existan comandos oficiales, realizar como mínimo estas
verificaciones manuales:

```powershell
docker compose up --build
docker compose ps
docker compose logs api
```

Para el frontend, verificar que el build existente termine correctamente:

```powershell
cd frontend
npm ci
npm run build
```

## 24. Linting y formato

No se encontraron configuraciones de formatter, linter o type checker
dedicadas en el repositorio actual.

> **Pendiente de configuración:** no ejecutar herramientas adicionales como
> parte de un procedimiento oficial hasta que el equipo las incorpore al
> proyecto.

El build frontend sí ejecuta el compilador TypeScript mediante `tsc -b`, como
parte del script `npm run build`.

## 25. Docker y limpieza

Comandos habituales:

```powershell
docker compose ps
docker compose logs
docker compose restart
docker compose down
```

`docker compose down` detiene y elimina los contenedores, pero conserva los
volúmenes declarados por el proyecto.

No usar `docker compose down -v` como procedimiento normal: elimina los
volúmenes `postgres_data` y `redis_data`, y puede borrar datos locales del
entorno.

## 26. Archivos que no deben subirse a GitHub

Mantener fuera del repositorio, como mínimo:

```text
.env
.venv/
node_modules/
__pycache__/
*.pyc
logs/
*.log
```

También deben excluirse claves privadas, tokens, dumps de base de datos,
artefactos de compilación y cualquier archivo sensible generado localmente.
Mantener el `.gitignore` actualizado antes de hacer `git add .`.

## 27. Flujo de trabajo recomendado para el equipo

```text
GitHub
   ↓
git clone
   ↓
Repositorio local
   ↓
Crear rama
   ↓
Desarrollar
   ↓
Probar
   ↓
Commit
   ↓
Push
   ↓
Pull Request
   ↓
Revisión
   ↓
Merge
```

Cada integrante debe trabajar en su propia rama y mantenerla sincronizada con
la rama base antes de solicitar la revisión.

## 28. Solución de problemas

| Problema | Posible causa | Solución |
| --- | --- | --- |
| `git` no se reconoce | Git no está instalado o no está en `PATH` | Instalar Git, abrir una terminal nueva y ejecutar `git --version`. |
| Docker no responde | Docker Desktop/Engine no está iniciado | Iniciar Docker y repetir `docker info` y `docker compose version`. |
| `docker compose` no se reconoce | Falta el complemento Compose | Actualizar Docker Desktop o instalar el complemento Docker Compose. |
| Un servicio no inicia | Imagen no descargada, variable ausente o error de configuración | Ejecutar `docker compose logs <servicio>` y revisar `.env`. |
| No abre `http://localhost:8081` | El contenedor `web` no está activo o el puerto está ocupado | Ejecutar `docker compose ps`, revisar logs y cambiar `WEB_PORT` si es necesario. |
| Error de conexión a PostgreSQL | `postgres` no está saludable o `DATABASE_URL` no coincide | Revisar `docker compose ps`, logs de `postgres` y la configuración local. |
| Error de conexión a Redis | `redis` no está saludable o `REDIS_URL` es incorrecta | Revisar logs de `redis` y la variable `REDIS_URL`. |
| Falla `pip install` | Python/entorno virtual incorrecto o problema de red | Activar `.venv`, verificar `python --version` y repetir con `requirements.txt`. |
| Falla `npm ci` | Lockfile desactualizado o versión de Node incompatible | Usar Node 22, ejecutar desde `frontend` y revisar `package-lock.json`. |
| Cambios no aparecen en el contenedor | La imagen no fue reconstruida | Ejecutar `docker compose up --build`. |
| Conflictos al actualizar Git | La rama local y la remota modificaron las mismas líneas | Revisar `git status`, resolver los archivos marcados y finalizar el merge/rebase. |

## 29. Comandos rápidos

```powershell
git pull
git status
git checkout -b feature/nueva-funcionalidad
git add .
git commit -m "feat: nueva funcionalidad"
git push -u origin feature/nueva-funcionalidad

docker compose up -d
docker compose up --build
docker compose ps
docker compose logs
docker compose restart
docker compose down
```

## 30. Checklist para una nueva estación de trabajo

- [ ] Git instalado.
- [ ] Docker instalado.
- [ ] Docker Compose funcionando.
- [ ] Python instalado si se ejecuta el backend fuera de Docker.
- [ ] Node.js y npm instalados si se ejecuta el frontend fuera de Docker.
- [ ] GitHub autenticado.
- [ ] Repositorio clonado.
- [ ] `.env` creado y configurado localmente.
- [ ] Dependencias instaladas si se trabaja fuera de Docker.
- [ ] Contenedores funcionando con `docker compose ps`.
- [ ] PostgreSQL y Redis saludables.
- [ ] Esquema de base de datos inicializado por el backend.
- [ ] Migraciones Alembic ejecutadas, cuando Alembic esté configurado.
- [ ] Backend funcionando.
- [ ] Frontend accesible en `http://localhost:8081`.
- [ ] Build frontend ejecutado.
- [ ] Pruebas ejecutadas, cuando existan suites automatizadas.
