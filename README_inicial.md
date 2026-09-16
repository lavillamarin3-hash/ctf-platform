# Plataforma CTF del laboratorio

Primera entrega funcional de una plataforma CTF interna para el laboratorio MITRE ATT&CK. Implementa FastAPI, React/TypeScript, PostgreSQL, Redis, Docker Compose, control de acceso por roles, retos iniciales, validación de flags, ranking en tiempo real y el ciclo de una conexión exclusiva a Guacamole.

## Arranque local

1. Copia `.env.example` como `.env` y sustituye sus secretos.
2. Ejecuta `docker compose up --build`.
3. Abre `http://localhost:8080`.

En modo de demostración se crean las cuentas `admin`, `instructor`, `usuario` y `guest`. Todas usan el valor de `CTF_DEMO_PASSWORD`. Estas cuentas existen solo para la primera instalación de desarrollo; cámbialas o desactívalas antes de una sesión real.

La API queda disponible tras el proxy en `/api/v1` y su documentación en `/docs`.

## Integración con el laboratorio

- Sitúa `LAB-CTFWEB` en la VLAN de administración y permite el acceso humano desde las estaciones autorizadas a través de Guacamole.
- Mantén el segmento de monitoreo aislado: la aplicación no se comunica con Security Onion.
- El adaptador predeterminado de Guacamole (`GUACAMOLE_MODE=stub`) permite probar el ciclo de inicio/cierre sin modificar la infraestructura.
- Antes de seleccionar `GUACAMOLE_MODE=managed`, implementa y pruebe el adaptador para la versión y autenticación instaladas de Guacamole. No almacenes credenciales de usuarios o de máquinas objetivo en el frontend.
- La plataforma modela el control de escenario y la restauración de snapshots como puertos. No modifica automáticamente firewall, Nutanix ni máquinas víctima.

## Arquitectura

El backend mantiene el núcleo de negocio en servicios y puertos explícitos. Los adaptadores de PostgreSQL, Redis, WebSockets y Guacamole se encuentran fuera de los casos de uso. Las asignaciones de acceso remoto se crean al iniciar un reto y se revocan al cerrarlo o expirar.

Los retos semilla corresponden al mapeo acordado: ESC-01-RECON (Básico, 100), ESC-02-BRUTEFORCE y ESC-03-WEBEXPLOIT (Medio, 250), y ESC-04-LATERAL y ESC-05-EXFIL (Avanzado, 500). Un reto de varias flags concede sus puntos una sola vez, cuando se completa.

## Seguridad operativa

- Las contraseñas y flags usan Argon2; el historial de intentos conserva únicamente un HMAC del valor enviado.
- Los intentos de flags están limitados por usuario y reto.
- Las URLs de Guacamole no contienen secretos y se asignan por usuario, reto y ejecución.
- Usa HTTPS con un proxy TLS del laboratorio antes de exponer la plataforma fuera de localhost.
- Las flags de los retos semilla deben configurarse desde el panel de instructor antes de publicar una sesión de entrenamiento.

## Estado de la interfaz (fase actual)

La plataforma incluye Login y vistas separadas por rol. El Jugador dispone de dashboard, categorías, catálogo, detalle de reto, envío de flags, progreso, ranking y laboratorio. El panel de Administración/Instructor permite gestionar el catálogo desde la interfaz: crear y editar retos, publicarlos o dejarlos inactivos y conservar el historial mediante archivado lógico. El Administrador puede además cambiar el rol y habilitar/deshabilitar usuarios. El ranking se muestra con datos reales calculados por el backend.

El modo claro utiliza una paleta de bajo deslumbramiento con contraste reforzado en textos, tablas, selectores y etiquetas de dificultad. La preferencia de tema se conserva en el navegador.

## Integración con el laboratorio

- Sitúa `LAB-CTFWEB` en la VLAN de administración y permite el acceso humano desde las estaciones autorizadas a través de Guacamole.
- Mantén el segmento de monitoreo aislado: la aplicación no se comunica con Security Onion.
- El adaptador predeterminado de Guacamole (`GUACAMOLE_MODE=stub`) permite probar el ciclo de inicio/cierre sin modificar la infraestructura.
- Antes de seleccionar `GUACAMOLE_MODE=managed`, implementa y pruebe el adaptador para la versión y autenticación instaladas de Guacamole. No almacenes credenciales de usuarios o de máquinas objetivo en el frontend.
- La plataforma modela el control de escenario y la restauración de snapshots como puertos. No modifica automáticamente firewall, Nutanix ni máquinas víctima.

## Arquitectura

El backend mantiene el núcleo de negocio en servicios y puertos explícitos. Los adaptadores de PostgreSQL, Redis, WebSockets y Guacamole se encuentran fuera de los casos de uso. Las asignaciones de acceso remoto se crean al iniciar un reto y se revocan al cerrarlo o expirar.

Los retos semilla corresponden al mapeo acordado: ESC-01-RECON (Básico, 100), ESC-02-BRUTEFORCE y ESC-03-WEBEXPLOIT (Medio, 250), y ESC-04-LATERAL y ESC-05-EXFIL (Avanzado, 500). Un reto de varias flags concede sus puntos una sola vez, cuando se completa.

## Seguridad operativa

- Las contraseñas y flags usan Argon2; el historial de intentos conserva únicamente un HMAC del valor enviado.
- Los intentos de flags están limitados por usuario y reto.
- Las URLs de Guacamole no contienen secretos y se asignan por usuario, reto y ejecución.
- Usa HTTPS con un proxy TLS del laboratorio antes de exponer la plataforma fuera de localhost.
- Las flags de los retos semilla deben configurarse desde el panel de instructor antes de publicar una sesión de entrenamiento.

## Estado de la interfaz (fase actual)

La fase actual del frontend está enfocada únicamente en **Login + experiencia del Jugador**. Se implementó una interfaz CTF oscura y responsive con navegación de jugador, dashboard, categorías, catálogo de retos, detalle del reto, envío de flags, progreso, ranking y acceso al laboratorio mediante las APIs existentes.

El panel de administración/instructor no se desarrolla en esta fase; el backend y sus endpoints existentes se conservan para una siguiente etapa.


## Fase UI actualizada — Login, jugador y vistas por rol

Esta versión incorpora: modo oscuro/claro persistente, texto actualizado de selección de reto y vistas diferenciadas para Administrador, Instructor, Jugador e Invitado. La vista de Administración incluye un inventario conceptual de 11 activos/VMs previstos para la integración futura con Nutanix AHV, sin afirmar que todavía estén conectados a Prism.

### Arranque con Docker en Windows

1. Copia `.env.example` a `.env` y cambia las contraseñas/secretos.
2. El puerto web por defecto es `8081`, configurable con `WEB_PORT`.
3. Ejecuta `docker compose up --build`.
4. Abre `http://localhost:8081`.

Para una instalación nueva en Windows CMD: `copy .env.example .env`. No versionar el archivo `.env`.


## Fase 3 — categorías y catálogo de retos

Esta versión añade un modelo explícito de categoría y escenario al reto, un catálogo de datos demo y una vista de detalle más completa. Los retos demo están pensados para mostrar el flujo de la interfaz; las flags demo solo se incluyen cuando `CTF_SEED_DEMO_DATA=true`.

### Categorías demo

WEB, CRIPTOGRAFÍA, FORENSE, REVERSING, PWN / EXPLOITING, OSINT, ESTEGANOGRAFÍA y MISC.

### Nota de base de datos

El arranque aplica `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para añadir `category` y `scenario` en instalaciones que ya tenían el volumen PostgreSQL creado por versiones anteriores.

- Fase 5 UI: detalle del reto con paneles desplegables, laboratorio ampliado, envío de flag destacado y ranking de demostración Top 10 con distintivos para los tres primeros puestos.
