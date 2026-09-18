# Arquitectura Fase 11 — organización del código

## Objetivo

La aplicación se reorganiza para facilitar mantenimiento y futuras ampliaciones sin cambiar de forma innecesaria la funcionalidad existente.

## Frontend: MVC adaptado a React

- `models/`: tipos de dominio compartidos.
- `services/api/`: comunicación HTTP por dominio.
- `controllers/`: estado, efectos y acciones de cada caso de uso de interfaz.
- `views/`: composición de pantallas y presentación.
- `components/`: piezas visuales reutilizables.
- `styles/`: hojas CSS separadas por responsabilidad.
- `pages/`: puntos de entrada de alto nivel.

### Flujo

`View → Controller → API Service → Backend`

Las vistas no deben contener llamadas `fetch` ni reglas de negocio.

## Backend: separación por capas

- `api/`: routers HTTP por dominio.
- `services/`: casos de uso y adaptadores compartidos.
- `models.py`: entidades ORM.
- `schemas.py`: contratos Pydantic.
- `guacamole.py`: integración existente de Guacamole.
- `main.py`: composition root; registra middleware y routers.

### Flujo

`Router → Service/Use Case → Repository/ORM → Infraestructura`

Cuando se implemente el ciclo completo de banderas dinámicas se añadirá la separación Hexagonal/Strategy/Repository/Observer definida en los documentos 19 y 20.

## CSS

`frontend/src/styles.css` es ahora un punto de entrada pequeño. Los estilos se agrupan por responsabilidad:

- foundation
- theme/auth
- accessibility/laboratory
- flags
- ui polish
- layout
- admin
- tables/forms
- responsive
- sidebar
- assignments
- player connections
- groups layout
- groups panels
- groups theme/responsive

No se debe volver a crear un `styles.css` monolítico.

## Regla de mantenimiento

Mantener los archivos de código por debajo de 1000 líneas. Cuando un módulo crezca, separar por responsabilidad en lugar de duplicar lógica.

## Compatibilidad

`frontend/src/api.ts` permanece como fachada para no obligar a modificar todos los componentes de una sola vez. Los nuevos endpoints deben implementarse dentro de `services/api/` y exponerse desde la fachada.
