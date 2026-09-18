# Refactorización Fase 11 — guía de mantenimiento

## 1. Principio general

La aplicación se divide por responsabilidad. Una pantalla no debe contener simultáneamente estado, llamadas HTTP, lógica de negocio y cientos de reglas visuales.

## 2. Frontend

### Models

`src/models/` contiene únicamente tipos de datos. Aquí se agregan o modifican contratos de usuario, reto, grupo, laboratorio, VM, Guacamole, ranking y ejecución.

### Services

`src/services/api/` contiene la comunicación HTTP agrupada por dominio:

- `auth.api.ts`: login, perfil y contraseña.
- `users.api.ts`: usuarios de la plataforma.
- `guacamole.api.ts`: usuarios, conexiones y permisos remotos.
- `challenges.api.ts`: retos, runs y flags.
- `groups.api.ts`: grupos, miembros y asignaciones.
- `laboratories.api.ts`: laboratorios y VMs.
- `reports.api.ts`: exportaciones.
- `client.ts`: token y cliente HTTP común.

`src/api.ts` es una fachada de compatibilidad. No se debe volver a convertirla en un archivo monolítico.

### Controllers

`src/controllers/` contiene hooks que coordinan estado, efectos y acciones.

- `useManagementController.ts`: administración.
- `usePlayerController.ts`: portal del jugador.

Los controllers no deben devolver JSX.

### Views

`src/views/management/` y `src/views/player/` contienen las pantallas. Una vista puede consumir varios componentes, pero no debe implementar llamadas HTTP directamente.

### Components

`src/components/` contiene piezas reutilizables. Los componentes de mayor tamaño deben dividirse antes de superar 1000 líneas.

## 3. Backend

### API

`backend/app/api/` contiene routers separados por dominio. Aquí se validan parámetros HTTP, roles y permisos de acceso.

### Services

`backend/app/services/` concentra lógica compartida y casos de uso extraídos del antiguo `main.py`.

### Composition root

`backend/app/main.py` registra middleware, ciclo de vida y routers. No debe volver a almacenar todos los endpoints.

## 4. CSS

`src/styles.css` es únicamente el punto de entrada.

Los módulos CSS se ordenan por responsabilidad y mantienen una cascada conocida:

1. foundation
2. theme/auth
3. accessibility/lab
4. flags
5. UI polish
6. layout
7. admin
8. tables/forms
9. responsive
10. sidebar
11. assignments
12. player connections
13. groups layout
14. groups forms
15. groups panels
16. groups theme/responsive

Cuando un módulo CSS crezca demasiado, dividirlo manteniendo el orden en `styles.css`.

## 5. Regla de tamaño

Objetivo de mantenimiento: ningún archivo de TypeScript, TSX, Python o CSS debe superar 1000 líneas.

La separación debe hacerse por responsabilidad y no por cortes arbitrarios.

## 6. Comentarios

Cada módulo comienza con un encabezado que explica su responsabilidad. Las funciones que coordinan operaciones importantes deben documentar qué hacen y por qué.

Evitar comentarios que repitan literalmente el nombre de la función.

## 7. Siguiente fase

El sistema de banderas dinámicas de los documentos 19 y 20 se implementará sobre esta estructura, manteniendo:

- generación por instancia;
- validación contra la instancia activa del usuario;
- ciclo restaurar → inyectar → habilitar Guacamole → usar → revocar → restaurar;
- Strategy, Repository y Observer para el backend;
- integración con Prism Element y Guacamole mediante adaptadores.

La refactorización de esta fase no pretende marcar esos puntos como implementados; solo deja el código preparado para incorporarlos sin volver a crear módulos monolíticos.
