# Fase 11 — Reorganización MVC conservando el proyecto existente

Esta versión parte del proyecto CTF existente y conserva su funcionalidad y archivos de aplicación, incorporando una reorganización gradual para facilitar futuras modificaciones.

## Frontend
- `controllers/`: estado y acciones de las pantallas.
- `models/`: tipos de dominio del frontend.
- `services/api/`: llamadas HTTP separadas por dominio.
- `views/`: vistas de gestión y jugador.
- `components/shared/`: componentes reutilizables.
- `styles/`: CSS modular por responsabilidad.
- `styles.css`: punto de entrada del CSS.

## Backend
- `api/`: routers/endpoints por módulo.
- `services/`: lógica de aplicación reutilizable.
- Los archivos existentes (`models.py`, `schemas.py`, `db.py`, etc.) se conservan para evitar una migración destructiva.

## Regla de mantenimiento
Los cambios nuevos deben agregarse en el módulo correspondiente y evitar archivos monolíticos. Los CSS se separan por responsabilidad y los comentarios deben explicar la responsabilidad del módulo, no repetir cada línea.

## Paso siguiente
Implementar el sistema de banderas dinámicas definido en los documentos de arquitectura y prompt de implementación, sin mezclarlo con la lógica visual.
