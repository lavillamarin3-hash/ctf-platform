# Eliminar un reto definitivamente

1. Entra como **administrador** y abre **Retos**.
2. Localiza el reto y pulsa **Eliminar definitivamente**.
3. Revisa la vista previa: indica cuántas corridas, flags, entregas, pistas,
   asignaciones e historiales se eliminarán y cuántos puntos desaparecerán.
4. Si existen corridas activas o limpieza pendiente, ciérralas y vuelve a abrir
   la vista previa. Que el tiempo haya vencido no confirma que el laboratorio
   haya terminado de limpiarse.
5. Escribe el código del reto exactamente como aparece y confirma la eliminación.

Esta acción borra el reto y sus datos asociados de la base de datos. También
quita del ranking los puntos obtenidos en ese reto. No se puede deshacer desde
la plataforma. Si solo deseas ocultarlo y conservar los resultados, utiliza
**Desactivar**.

Los usuarios, grupos, membresías y máquinas virtuales se conservan. También se
conserva una auditoría con el administrador, el código del reto y los recuentos;
no contiene flags ni contraseñas. Esta auditoría impide que un reinicio o una
configuración automática del catálogo vuelvan a crear el reto eliminado.

Solo el administrador puede eliminar definitivamente. El instructor conserva
sus opciones de creación, edición y archivo. Si aparece un aviso de permisos de
Guacamole pendientes después de eliminar ESC-01-RECON, el borrado ya terminó:
revisa la sincronización del laboratorio antes de reutilizar sus permisos.

## Comprobación técnica

No hace falta una migración de esquema. La operación es una transacción SQL:
se borran primero las tablas dependientes y después el reto, junto con su
auditoría. Un fallo antes de confirmar revierte todo. Las corridas nuevas usan
el mismo bloqueo de fila para evitar iniciar un reto durante su eliminación.

Los endpoints son:

- `GET /api/v1/challenges/{code}/deletion-preview`.
- `DELETE /api/v1/challenges/{code}/permanent`, con JSON
  `{"confirm_code":"CODIGO-EXACTO"}`.
- `DELETE /api/v1/challenges/{code}` sigue archivando sin borrar historial.

Pruebas aisladas de API/roles y SQLite con claves foráneas:

```bash
python -m unittest tests.test_challenge_deletion tests.test_deletion_start_lock -q
```

Aceptación con PostgreSQL real, únicamente sobre registros QA temporales y con
rollback obligatorio de todos sus datos al terminar:

```bash
PYTHONPATH=/app python tests/integration_challenge_deletion.py
```
