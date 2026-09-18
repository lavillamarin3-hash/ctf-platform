# Frontend — Componentes y Arquitectura SPA
> **Fuente:** `frontend/src/` · **Generado:** 2026-09-17 · **Estado:** MVP funcional

---

## Tabla de Contenidos

1. [Stack y dependencias](#1-stack-y-dependencias)
2. [Estructura de archivos](#2-estructura-de-archivos)
3. [Enrutamiento por rol (App.tsx)](#3-enrutamiento-por-rol-apptsx)
4. [Módulo de comunicación con la API (api.ts)](#4-módulo-de-comunicación-con-la-api-apits)
5. [Configuración y tipos compartidos (config.ts)](#5-configuración-y-tipos-compartidos-configt)
6. [Vistas principales por rol](#6-vistas-principales-por-rol)
7. [Componentes reutilizables](#7-componentes-reutilizables)
8. [Gestión del estado asíncrono](#8-gestión-del-estado-asíncrono)
9. [WebSocket y tiempo real](#9-websocket-y-tiempo-real)
10. [Sistema de temas (dark/light)](#10-sistema-de-temas-darklight)
11. [Tipos TypeScript exportados](#11-tipos-typescript-exportados)
12. [Brecha con el MVP objetivo](#12-brecha-con-el-mvp-objetivo)

---

## 1. Stack y Dependencias

| Herramienta | Versión | Rol |
|---|---|---|
| React | 18.3.1 | UI Library (hooks, no class components) |
| TypeScript | 5.7.3 | Tipado estático |
| Vite | 5.4.14 | Bundler + dev server (HMR) |
| TailwindCSS | 3.4.17 | Estilos utility-first |
| PostCSS + Autoprefixer | 8.5.1 / 10.4.20 | Procesamiento CSS |

**Build:** `tsc -b && vite build` → artefactos en `dist/`
**Imagen producción:** `nginx:1.27-alpine` con los artefactos copiados

---

## 2. Estructura de Archivos

`
frontend/src/
├── main.tsx              — Entry point: monta <App /> en el DOM
├── App.tsx               — Router principal: autenticación + despacho por rol
├── api.ts                — Cliente HTTP centralizado + tipos de dominio exportados
├── config.ts             — Tipos, constantes, opciones estáticas (sin API calls)
├── styles.css            — CSS global + capas Tailwind + clases de componentes custom
│
├── pages/                — Una página por rol (nivel de aplicación)
│   ├── AdminApp.tsx      — Re-exporta ManagementApp con panelRole="admin"
│   ├── InstructorApp.tsx — Re-exporta ManagementApp con panelRole="instructor"
│   ├── ManagementApp.tsx — Panel unificado admin+instructor (1 947 líneas, ~8 vistas)
│   ├── PlayerApp.tsx     — Panel del jugador (957 líneas, ~6 vistas)
│   └── GuestApp.tsx      — Vista de invitado (369 líneas, catálogo de solo lectura)
│
└── components/           — Componentes reutilizables por dominio
    ├── auth.tsx          — Formulario de login con validación
    ├── challenges.tsx    — ChallengeCard, ChallengeDetail, ChallengeForm
    ├── common.tsx        — Sidebar, Header, StatCard, Ranking, RecentActivity, Icon
    ├── groups.tsx        — GroupManagement, GroupForm, MembersPanel
    ├── guacamole.tsx     — GuacamoleUserForm, GuacamoleConnectionForm, PermissionsForm
    ├── laboratory.tsx    — LaboratoryForm, VMForm, mappers Backend→Frontend
    └── users.tsx         — UserForm: creación y edición de cuentas
`

---

## 3. Enrutamiento por Rol (App.tsx)

`App.tsx` es el único componente con responsabilidad de enrutamiento. No usa ninguna librería de router (React Router, etc.) — el estado `view` dentro de cada panel controla la vista activa mediante un switch interno.

### Flujo de inicio de la aplicación

`
montaje App
  │
  ├─ ¿hay token en sessionStorage?
  │    └─ sí → api.me() → setUser(User)
  │           ↳ error → session.clear() + setUser(null)
  │    └─ no → setChecking(false)
  │
  ├─ checking = true → <LoadingScreen> ("Recuperando sesión…")
  │
  ├─ user = null → <Login onLogin={setUser} />
  │
  └─ user con rol → switch(user.role)
       "admin"      → <AdminApp>
       "instructor" → <InstructorApp>
       "player"     → <PlayerApp>
       "guest"      → <GuestApp>
`

### Props que fluyen desde App a cada panel

`	ypescript
{
  user: User,
  onLogout: () => void,          // session.clear() + setUser(null)
  theme: Theme,                  // "dark" | "light"
  onToggleTheme: () => void,
  themePreference: ThemePreference, // "system" | "dark" | "light"
  onThemePreferenceChange: (v) => void,
  onUserChange: (user: User) => void // para actualizar perfil sin re-login
}
`

---

## 4. Módulo de Comunicación con la API (api.ts)

### Función base `request<T>`

`	ypescript
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  // 1. Agrega Content-Type: application/json
  // 2. Agrega Authorization: Bearer <token> si hay sesión
  // 3. fetch(/api/v1, ...)
  // 4. Si !response.ok → throw new Error(body.detail || "...")
  // 5. return body as T
}
`

- **Base URL:** `/api/v1` (relativa; el proxy Nginx resuelve al backend)
- **Token:** Se lee de `sessionStorage` en cada llamada (no en closure)
- **Error:** Lanza `Error` con el campo `detail` del JSON de error de FastAPI

### Gestión de sesión

`	ypescript
const tokenKey = "ctf-access-token";
export const session = {
  get:   () => sessionStorage.getItem(tokenKey),
  save:  (token) => sessionStorage.setItem(tokenKey, token),
  clear: () => sessionStorage.removeItem(tokenKey),
};
`

> **sessionStorage** vs localStorage: el token se descarta al cerrar el tab/ventana. Comportamiento intencional para entornos de laboratorio compartido.

### Inventario de métodos de la API

| Categoría | Método | Endpoint |
|---|---|---|
| Auth | `api.login(user, pass)` | `POST /auth/login` |
| Auth | `api.me()` | `GET /auth/me` |
| Auth | `api.updateProfile(input)` | `PATCH /auth/profile` |
| Auth | `api.changePassword(input)` | `POST /auth/password` |
| Retos | `api.challenges(params)` | `GET /challenges?...` |
| Retos | `api.categories()` | `GET /categories` |
| Retos | `api.createChallenge(input)` | `POST /challenges` |
| Retos | `api.updateChallenge(code, input)` | `PUT /challenges/{code}` |
| Retos | `api.archiveChallenge(code)` | `DELETE /challenges/{code}` |
| Flags | `api.createFlag(code, input)` | `POST /challenges/{code}/flags` |
| Flags | `api.updateFlag(code, flagId, input)` | `PUT /challenges/{code}/flags/{id}` |
| Flags | `api.deleteFlag(code, flagId)` | `DELETE /challenges/{code}/flags/{id}` |
| Runs | `api.start(code)` | `POST /challenges/{code}/start` |
| Runs | `api.runs()` | `GET /runs` |
| Runs | `api.closeRun(id)` | `POST /runs/{id}/close` |
| Submit | `api.submit(code, value)` | `POST /challenges/{code}/submissions` |
| Progreso | `api.progress()` | `GET /progress` |
| Ranking | `api.ranking()` | `GET /ranking` |
| Ranking | `api.downloadRanking()` | `GET /reports/ranking.csv` |
| Reporte | `api.progressReport(groupId?)` | `GET /reports/progress?group_id=` |
| Usuarios | `api.users()` | `GET /users` |
| Usuarios | `api.visibleUsers()` | `GET /users/visible` |
| Usuarios | `api.createUser(input)` | `POST /users` |
| Usuarios | `api.updateUser(id, changes)` | `PATCH /users/{id}` |
| Usuarios | `api.deleteUser(id)` | `DELETE /users/{id}` |
| Grupos | `api.groups()` | `GET /groups` |
| Grupos | `api.createGroup(input)` | `POST /groups` |
| Grupos | `api.updateGroup(id, input)` | `PATCH /groups/{id}` |
| Grupos | `api.deleteGroup(id)` | `DELETE /groups/{id}` |
| Grupos | `api.addGroupMember(gId, uId)` | `POST /groups/{id}/members` |
| Grupos | `api.removeGroupMember(gId, uId)` | `DELETE /groups/{id}/members/{uid}` |
| Grupos | `api.assignChallengeGroup(code, gId)` | `PUT /challenges/{code}/groups/{gid}` |
| Grupos | `api.unassignChallengeGroup(code, gId)` | `DELETE /challenges/{code}/groups/{gid}` |
| Grupos | `api.listGroupRemoteConnections(gId)` | `GET /groups/{id}/remote-connections` |
| Grupos | `api.createGroupRemoteConnections(gId, input)` | `POST /groups/{id}/remote-connections` |
| Labs | `api.laboratories()` | `GET /laboratories` |
| Labs | `api.playerLaboratories()` | `GET /player/laboratories` |
| Labs | `api.createLaboratory(input)` | `POST /laboratories` |
| Labs | `api.updateLaboratory(id, input)` | `PATCH /laboratories/{id}` |
| Labs | `api.deleteLaboratory(id)` | `DELETE /laboratories/{id}` |
| VMs | `api.createVM(input)` | `POST /vms` |
| VMs | `api.updateVM(id, input)` | `PATCH /vms/{id}` |
| VMs | `api.deleteVM(id)` | `DELETE /vms/{id}` |
| Guacamole | `api.guacamoleStatus()` | `GET /admin/guacamole/status` |
| Guacamole | `api.guacamoleUsers()` | `GET /admin/guacamole/users` |
| Guacamole | `api.guacamoleConnections()` | `GET /admin/guacamole/connections` |
| Guacamole | `api.guacamolePermissions(user)` | `GET /admin/guacamole/users/{u}/permissions` |
| Guacamole | `api.updateGuacamolePermissions(user, input)` | `PATCH /admin/guacamole/users/{u}/permissions` |

---

## 5. Configuración y Tipos Compartidos (config.ts)

Concentra constantes y tipos sin lógica de presentación ni llamadas a la API.

### Tipos de vistas por panel

`	ypescript
// Vistas del panel del jugador
type PlayerView = "dashboard" | "categories" | "challenges" | "progress" | "ranking" | "laboratory";

// Vistas del panel de administración/instructor
type ManagementView = "dashboard" | "challenges" | "users" | "laboratory" | "ranking" | "groups" | "monitoring" | "guacamole";
`

### Categorías de retos (con metadatos visuales)

`	ypescript
const categoryMeta: Record<string, { icon: string; tone: string }> = {
  WEB:                { icon: "⌁",   tone: "blue"   },
  CRIPTOGRAFÍA:       { icon: "◈",   tone: "amber"  },
  FORENSE:            { icon: "⌕",   tone: "green"  },
  REVERSING:          { icon: "</>", tone: "violet" },
  "PWN / EXPLOITING": { icon: "›_",  tone: "red"    },
  OSINT:              { icon: "◎",   tone: "cyan"   },
  ESTEGANOGRAFÍA:     { icon: "▧",   tone: "pink"   },
  MISC:               { icon: "✦",   tone: "slate"  },
};
`

### Estilos de dificultad (Tailwind)

`	ypescript
const difficultyStyle = {
  Básico:   "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  Medio:    "border-amber-400/30 bg-amber-400/10 text-amber-300",
  Avanzado: "border-rose-400/30 bg-rose-400/10 text-rose-300",
};
`

### Inventario de SO para VMs

`	ypescript
const VM_OS_OPTIONS = [
  "Windows 10 (ES)",
  "Ubuntu Server 26.04",
  "Linux Mint",
  "Kali Linux Purple 2026.2",
  "Kali Linux 2026.2",
];
`

### Funciones de usuario (para perfil)

`Estudiante · Instructor · Tutor · Analista SOC · Red Team · Blue Team · Administrador de laboratorio · Coordinador · Otro`

---

## 6. Vistas Principales por Rol

### 6.1 Vista del Jugador (PlayerApp.tsx — 957 líneas)

**Vistas disponibles:**

| Vista (`view`) | Descripción |
|---|---|
| `dashboard` | Panel resumen: StatCards (puntos, retos completados), ChallengeDetail del reto seleccionado, Ranking en tiempo real, actividad reciente |
| `categories` | Cuadrícula de CategoryCards; al hacer clic filtra los retos por categoría |
| `challenges` | Lista de ChallengeCards filtrable por dificultad y categoría |
| `progress` | Estado de cada reto (completado / pendiente) con puntos obtenidos |
| `ranking` | Scoreboard completo con posiciones, puntos y retos completados |
| `laboratory` | Inventario de VMs accesibles; botón "Acceder" → URL Guacamole en iframe o pestaña nueva |

**Estado del panel (React state):**

| Estado | Tipo | Origen |
|---|---|---|
| `challenges` | `Challenge[]` | `api.challenges()` |
| `ranking` | `RankingRow[]` | `api.ranking()` + WebSocket |
| `runs` | `Run[]` | `api.runs()` |
| `laboratories` | `BackendLaboratory[]` | `api.playerLaboratories()` |
| `progress` | `{total_points, challenges_completed}` | `api.progress()` |
| `selectedCode` | `string\|null` | Selección del jugador |
| `filter` | `string` | Filtro de dificultad |
| `categoryFilter` | `string` | Filtro de categoría |
| `view` | `PlayerView` | Navegación interna |

**Carga de datos:** `Promise.all([api.challenges(), api.ranking(), api.runs(), api.progress(), api.playerLaboratories()])` en `useEffect` inicial y después de acciones que modifican estado.

---

### 6.2 Vista del Invitado (GuestApp.tsx — 369 líneas)

Panel de solo lectura. Muestra el catálogo de retos (sin instrucciones ni referencias de activos, filtradas por el backend) y el ranking. No tiene acceso a laboratorios, ni a envío de flags.

**Vistas disponibles:** `dashboard` · `challenges` · `ranking`

---

### 6.3 Panel de Administración/Instructor (ManagementApp.tsx — 1 947 líneas)

`AdminApp.tsx` e `InstructorApp.tsx` son envoltorios delgados que invocan `ManagementApp` con `panelRole="admin"` o `panelRole="instructor"`. Las diferencias de acceso se controlan por prop.

**Vistas del panel (`ManagementView`):**

| Vista | Acceso | Descripción |
|---|---|---|
| `dashboard` | admin, instructor | Resumen: total retos, jugadores, puntos, grupos. StatCards + ranking parcial |
| `challenges` | admin, instructor | CRUD de retos y flags. ChallengeForm inline. Asignación a grupos |
| `users` | admin | CRUD de usuarios CTF + sincronización con Guacamole. UserForm con campos de perfil |
| `groups` | admin | Gestión de grupos: CRUD, miembros (búsqueda por username), asignación de retos, conexiones Guacamole del grupo |
| `laboratory` | admin | CRUD de laboratorios y VMs. LaboratoryForm + VMForm |
| `ranking` | admin, instructor | Ranking completo con opción de descarga CSV |
| `monitoring` | admin, instructor | Matriz de progreso usuario×reto por grupo. Filtro por grupo |
| `guacamole` | admin | Administración directa: estado, usuarios, conexiones, permisos de Guacamole |

**Estado del panel (selección):**

| Estado | Tipo | Origen |
|---|---|---|
| `challenges` | `Challenge[]` | `api.challenges()` |
| `users` | `ManagedUser[]` | `api.users()` / `api.visibleUsers()` |
| `groups` | `StudentGroup[]` | `api.groups()` |
| `laboratories` | `Laboratory[]` | `api.laboratories()` (mapeado) |
| `guacamoleUsers` | `GuacamoleUser[]` | `api.guacamoleUsers()` |
| `guacamoleConnections` | `GuacamoleConnection[]` | `api.guacamoleConnections()` |
| `progressRows` | `ProgressRow[]` | `api.progressReport(groupId)` |
| `rankingRows` | `RankingRow[]` | `api.ranking()` |

---

## 7. Componentes Reutilizables

### `components/auth.tsx`

| Componente | Props principales | Descripción |
|---|---|---|
| `Login` | `onLogin, theme, onToggleTheme` | Formulario de autenticación. Maneja estado de loading, error y llamada a `api.login()`. Guarda token en sessionStorage y llama `onLogin` con el objeto User |

---

### `components/challenges.tsx`

| Componente | Props principales | Descripción |
|---|---|---|
| `ChallengeCard` | `challenge, completed, onSelect` | Tarjeta visual de reto: código, nombre, categoría, dificultad, puntos, badge de completado |
| `ChallengeDetail` | `challenge, run, onStart, onSubmit, ...` | Vista detallada: descripción, instrucciones, assets, formulario de envío de flag, botones start/close, URL de Guacamole |
| `ChallengeForm` | `initial, onSubmit, onCancel` | Formulario completo para crear/editar retos: todos los campos con validación inline |
| `inferCategory(challenge)` | — | Función helper: infiere la categoría visual desde `challenge.category` usando `categoryMeta` |

---

### `components/common.tsx`

| Componente | Descripción |
|---|---|
| `PlayerSidebar` | Barra lateral con ítems de navegación para el jugador. Destaca la vista activa |
| `ManagementSidebar` | Barra lateral para admin/instructor. Filtrada por `panelRole` |
| `GuestSidebar` | Barra lateral minimal para invitados |
| `Header` | Barra superior: nombre de usuario, rol, toggle de tema, botón de logout |
| `StatCard` | Tarjeta de estadística: icono, valor, label, color de acento |
| `CategoryCard` | Tarjeta de categoría: icono, nombre, conteo de retos, color |
| `Ranking` | Tabla de clasificación: posición (con medallas para top 3), username, puntos, retos |
| `RecentActivity` | Lista de últimas actividades del jugador (runs recientes) |
| `Icon` | Componente de icono SVG inline usando strings de nombre |

---

### `components/groups.tsx`

| Componente | Descripción |
|---|---|
| `GroupManagement` | Vista completa de gestión de grupos: lista, formulario CRUD, panel de miembros, asignación de retos, panel de conexiones Guacamole |

---

### `components/guacamole.tsx`

| Componente | Descripción |
|---|---|
| `GuacamoleUserForm` | Formulario para crear/editar usuario en Guacamole |
| `GuacamoleConnectionForm` | Formulario para crear/editar conexión (SSH/RDP/VNC) con campos de host, puerto, credenciales |
| `GuacamolePermissionsForm` | Editor de permisos de sistema y permisos de conexión por usuario |

---

### `components/laboratory.tsx`

| Componente / Función | Descripción |
|---|---|
| `LaboratoryForm` | Formulario para crear/editar laboratorio: código, nombre, descripción, segmento, estado |
| `VMForm` | Formulario para registrar VM: nombre, SO, IP (validada contra catálogo), VLAN, perfil, rol de red, ID Guacamole, ID Nutanix |
| `mapBackendLaboratory(lab)` | Convierte `BackendLaboratory` (API) → `Laboratory` (frontend config) |
| `mapBackendVM(vm)` | Convierte `BackendVM` (API) → `LabVM` (frontend config) |

---

### `components/users.tsx`

| Componente | Descripción |
|---|---|
| `UserForm` | Formulario de creación/edición de usuarios CTF: username, email, password, rol, nombre completo, organización, función, sync_guacamole. Renderiza campos de contraseña solo en creación |

---

## 8. Gestión del Estado Asíncrono

La SPA no usa ninguna librería de gestión de estado global (no Redux, Zustand, Context API para datos remotos). El estado se gestiona localmente en cada panel mediante `useState` + `useCallback` + `useEffect`.

### Patrón de carga paralela

`	ypescript
// PlayerApp.tsx - Carga inicial
const load = useCallback(async () => {
  try {
    const [all, rank, activeRuns, currentProgress, playerLabs] = await Promise.all([
      api.challenges(),
      api.ranking(),
      api.runs(),
      api.progress(),
      api.playerLaboratories(),
    ]);
    setChallenges(all);
    setRanking(rank.rows);
    setRuns(activeRuns);
    setProgress(currentProgress);
    setLaboratories(playerLabs);
  } catch (err) {
    setMessage(err instanceof Error ? err.message : "Error al cargar");
  }
}, [selectedCode]);

useEffect(() => { void load(); }, [load]);
`

### Patrón de re-carga post-mutación

Después de cualquier operación de escritura (submit, crear, editar, eliminar), el panel llama a `load()` para refrescar el estado desde el servidor. No hay optimistic updates.

`	ypescript
const handleSubmit = async (value: string) => {
  const result = await api.submit(code, value);
  setMessage(result.message);
  await load(); // refresca challenges (completed), ranking, progress
};
`

### Computed state con `useMemo`

Los filtros de dificultad y categoría no llaman a la API; filtran el array local:

`	ypescript
const visibleChallenges = useMemo(
  () => challenges.filter(item =>
    (filter === "Todas" || item.difficulty === filter) &&
    (categoryFilter === "Todas" || item.category === categoryFilter)
  ),
  [challenges, filter, categoryFilter]
);
`

---

## 9. WebSocket y Tiempo Real

El ranking se actualiza en tiempo real mediante WebSocket. Solo `PlayerApp` y `GuestApp` establecen la conexión.

### Ciclo de vida del WebSocket (PlayerApp.tsx)

`	ypescript
useEffect(() => {
  const token = session.get();
  if (!token) return;

  // Protocolo según HTTP/HTTPS del host
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(
    ${protocol}:///api/v1/ws/ranking?token=
  );

  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "ranking.updated") {
      setRanking(payload.rows);  // actualización reactiva sin re-fetch
    }
  };

  return () => ws.close();  // cleanup al desmontar
}, []);
`

### Formato del evento recibido

`json
{
  "type": "ranking.updated",
  "rows": [
    { "position": 1, "username": "player01", "total_points": 750, "challenges_completed": 3 },
    { "position": 2, "username": "player02", "total_points": 500, "challenges_completed": 2 }
  ]
}
`

> El ranking se recibe completo (no incremental) para simplificar el estado en el cliente.

---

## 10. Sistema de Temas (dark/light)

El tema se gestiona en `App.tsx` y se propaga hacia abajo como prop. Se persiste en `localStorage`.

### Preferencias disponibles

| Valor | Comportamiento |
|---|---|
| `"dark"` | Tema oscuro fijo |
| `"light"` | Tema claro fijo |
| `"system"` | Sigue `prefers-color-scheme` del sistema operativo |

### Implementación

`	ypescript
// App.tsx
useEffect(() => {
  const resolved = themePreference === "system"
    ? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")
    : themePreference;
  
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
  localStorage.setItem("ctf-theme", resolved);
  localStorage.setItem("ctf-theme-preference", themePreference);
}, [themePreference]);
`

Los estilos Tailwind usan el selector `[data-theme="dark"]` / `[data-theme="light"]` definido en `styles.css` (modo `class` de Tailwind).

---

## 11. Tipos TypeScript Exportados (api.ts)

Todos los tipos de dominio se definen en `api.ts` y se re-exportan desde `config.ts` para uso uniforme:

| Tipo | Descripción |
|---|---|
| `User` | Perfil de usuario: id, username, email, role, is_active, full_name, organization, user_function |
| `Flag` | Flag de reto: id, label, flag_order, is_active, mode, template |
| `Challenge` | Reto completo: todos los campos + completed, flag_count, flags opcional |
| `RankingRow` | Fila de ranking: position, username, total_points, challenges_completed |
| `Run` | Sesión de reto: estado, fechas, launch_url, target_vm, laboratory_code |
| `GuacamoleUser` | Usuario Guacamole: username, attributes, last_active |
| `GuacamoleStatus` | Estado del adaptador: mode, connected, base_url, data_source |
| `GuacamoleConnection` | Conexión: identifier, name, protocol, hostname, port, parameters |
| `GuacamolePermissionSet` | system_permissions + connection_permissions por ID |
| `BackendVM` | VM del servidor: todos los campos incluyendo guacamole_url, guacamole_protocol |
| `BackendLaboratory` | Laboratorio del servidor con lista de VMs |
| `StudentGroup` | Grupo: id, name, code, members[], challenges[] |
| `GroupMember` | Miembro: user_id, username, email, is_active |
| `GroupChallenge` | Reto asignado al grupo: challenge_id, code, name |
| `StudentRemoteConnection` | Conexión individual Guacamole de un estudiante |
| `ProgressRow` | Fila de reporte: user, challenge, status, attempts, points, completed_at |

---

## 12. Brecha con el MVP Objetivo

### Implementado ✅

- SPA funcional con enrutamiento por rol sin librerías externas
- Cliente HTTP centralizado con gestión automática de token y errores
- WebSocket para ranking en tiempo real
- Panel de jugador con dashboard, catálogo, progreso, laboratorio y ranking
- Panel de admin/instructor con gestión completa de retos, usuarios, grupos, laboratorios y Guacamole
- Panel de invitado de solo lectura
- Sistema de temas dark/light/system
- Todos los tipos TypeScript derivados del contrato del backend
- Formularios con validación inline para todos los recursos

### Pendiente para MVP completo ⬜

- **Gestión de estado global:** Considerar Context API o Zustand para evitar prop drilling en paneles grandes
- **React Router:** Para URLs navegables y soporte de historial del navegador (atrás/adelante)
- **Separación de vistas:** `ManagementApp.tsx` (1 947 líneas) y `PlayerApp.tsx` (957 líneas) deberían dividirse en componentes más pequeños por vista
- **Manejo de errores por recurso:** Los errores actualmente se muestran como mensaje global; se necesitan notificaciones toast por operación
- **Refresh automático:** No hay polling ni re-conexión automática del WebSocket tras una desconexión
- **Validación de formularios:** Usar una librería (react-hook-form, Zod) en lugar de validación manual
- **Tests de componentes:** No hay tests unitarios ni de integración para el frontend
- **Accesibilidad:** ARIA roles y navegación por teclado no están sistemáticamente cubiertos
- **Refresh token:** El endpoint de refresh no existe aún en el backend; el token de 20 min expira sin renovación automática
