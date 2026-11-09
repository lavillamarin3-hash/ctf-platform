# Validación de la instalación nueva

Fecha: 8 de noviembre de 2026. Entrega local para revisión y despliegue posterior, sin migrar datos históricos ni modificar las VM de Nutanix.

## Resultados comprobados

| Comprobación | Resultado y alcance |
| --- | --- |
| Backend, suite completa | 357 pruebas: 356 correctas y 1 omitida; incluye las 14 pruebas del dominio y aprovisionamiento nuevos. |
| Integración PostgreSQL | 8 pruebas correctas contra una base local desechable; no se utilizó la base operativa. |
| Frontend histórico | 40 pruebas correctas. No representan una prueba completa de la interfaz nueva. |
| Compilación TypeScript/Vite | Correcta para la variante histórica y para `VITE_FRESH_INSTALL=true`. |
| Interfaz nueva | Inspección visual local con respuestas simuladas: login, formulario rápido de cuatro campos, opciones avanzadas cerradas y habilitación de Guardar. |
| Compose nuevo | Configuración válida usando la plantilla y `--no-env-resolution`; no se arrancaron contenedores. |
| Helpers y scripts | Compilación Python y comprobación de sintaxis Bash; no ejecutados como root en las víctimas reales. |
| Repositorio | `git diff --check` sin errores de formato. SQL y diccionario generados desde los modelos. |

Las ocho pruebas de integración cubren: administrador inicial único; catálogo explícito, idempotente y en borrador; limpieza que bloquea nuevas reservas; propiedad de la flag y puntuación única; autenticación, cambio obligatorio de contraseña y bloqueo de publicación; mantenimiento del laboratorio; revocación de asignación; y dos inicios simultáneos sin sobrescribir recursos.

PostgreSQL local es **18.6**, con Python 3.11. La infraestructura prevista usa PostgreSQL **16** y la imagen API Python 3.12. Se añadió un trabajo de CI con PostgreSQL 16 y Python 3.12, pero no se ha ejecutado aquí: los resultados locales no equivalen a esa validación.

## Reproducir las comprobaciones

Desde `backend`, con dependencias de `requirements-test.txt` instaladas:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Para integración, crear antes una base **desechable local**, cuyo nombre termine en `_test`. Esta suite elimina y recrea sus tablas; nunca usar datos que se deban conservar. El código exige host localhost/127.0.0.1 y ese sufijo.

```bash
export FRESH_TEST_DATABASE_URL='postgresql+asyncpg://USUARIO:CLAVE@127.0.0.1:5432/cociber_refactor_test'
python -m unittest discover -s tests -p integration_fresh.py -v
```

Desde `frontend`:

```bash
node --test tests/*.cjs tests/*.mjs
npm run build
VITE_FRESH_INSTALL=true npm run build
```

Desde la raíz, sin crear un archivo de secretos:

```bash
docker compose --env-file deploy/fresh.env.example -f deploy/docker-compose.fresh.yml config --quiet --no-env-resolution
git diff --check
```

## Validaciones pendientes en el laboratorio

1. Construir las imágenes y comprobar PostgreSQL 16 y Redis 7 con la configuración privada del servidor.
2. Instalar y probar los helpers y las claves verificadas en LNXVICT, SRVWEB y Kali según [HELPERS_FRESH.md](HELPERS_FRESH.md).
3. Verificar permisos de DVWA y su tabla de evidencias; el helper nuevo no convierte automáticamente una tabla histórica incompatible.
4. Completar un piloto de ESC-02 y ESC-03, abrir una consola Guacamole real y comprobar teclado, sesión, expiración y cierre desde el navegador del jugador.
5. Probar reinicio del worker, caída de dependencias y limpieza de cuentas/conexiones reales antes de permitir una segunda corrida.
6. Ensayar backup/restauración en una base aparte y el procedimiento manual de snapshots.

ESC-01, ESC-04 y ESC-05 permanecen configurados y deshabilitados por decisión del usuario. Sus contratos e implementación faltantes se registran en [PENDIENTES_ESCENARIOS.md](PENDIENTES_ESCENARIOS.md). La reserva de dos víctimas para Windows A→B también pertenece a esa fase.

## Limpieza documental

Se eliminaron `build-error.txt` (log histórico de compilación) y `gitignore.txt` (copia inactiva de configuración), después de leerlos y buscar referencias. Se conservaron las guías y el código que soportan la instalación histórica. [AUDITORIA_ARCHIVOS.csv](AUDITORIA_ARCHIVOS.csv) registra la clasificación conservadora; una ausencia de referencia textual no se considera prueba suficiente para borrar un archivo.

El punto de entrada de la versión nueva es [INSTALACION_NUEVA_COCIBER.md](INSTALACION_NUEVA_COCIBER.md). No se debe combinar su compose ni su esquema con los de la plataforma histórica.
