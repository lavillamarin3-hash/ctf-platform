# Investigación con Kali y LNX-VICT

Este lote añade adquisición remota y lógica a cuatro retos existentes y refuerza ESC-07. Usa Kali `192.168.146.134` y el servicio HTTP de LNX-VICT `192.168.146.137:18082`. La plataforma abre Kali; las VMs deben estar encendidas.

| Reto | Trabajo del alumno |
| --- | --- |
| WEB-02 | Inspeccionar el cliente público y comparar solicitudes HTTP reales. Demostrar el fallo lógico de autenticación con contraseña incorrecta y recuperar sesión y rol. |
| WEB-06 | Consultar perfil/documentos, seguir la referencia del caso y demostrar el acceso indebido a un objeto ajeno. Identificar objeto, propietario y evidencia. |
| FOR-05 | Adquirir manifiesto y ocho artefactos desde la víctima, calcular SHA-256 en Kali e identificar la alteración con los hashes de adquisición y observado. |
| DFIR-01 | Adquirir Auth, HTTP, red y calibración desde la víctima; verificar sus hashes, corregir dos desfases y correlacionar cinco campos del incidente. |
| ESC-07-EXPOSED | Descubrir una carpeta variable, comparar tres respaldos con un manifiesto, descartar señuelos por versión y SHA-256 y reconstruir fragmentos codificados. |

WEB-02 y WEB-06 reproducen fallos de una aplicación HTTP de práctica en funcionamiento. FOR-05 y DFIR-01 conservan evidencias sintéticas: su adquisición sucede a través de las VMs y su resolución exige análisis. ESC-07 combina reconocimiento real con integridad y reconstrucción. Estos casos no publican una flag directamente dentro de un archivo.

Con LAB-01, ESC-01, ESC-02 y ESC-06 se completan nueve retos que dependen de las VMs. Los otros treinta y uno conservan ejercicios de lógica y archivos, con Kali como espacio de trabajo y descarga opcional.

## Recorrido del estudiante

1. Iniciar el reto y abrir la terminal Kali integrada.
2. Consultar desde Kali la URL inicial de la corrida. La página de la plataforma muestra objetivo y campos de respuesta, sin entregar las evidencias ni una receta completa.
3. Investigar el servicio, adquirir las fuentes necesarias y trabajar en una carpeta propia de la corrida.
4. Introducir los resultados y pulsar **Validar respuestas**. Una respuesta correcta permite registrar los puntos; la flag de transporte no se muestra en pantalla.
5. Cerrar el ejercicio. El cierre o la caducidad invalidan las rutas remotas y la terminal de esa corrida.

Las pistas y la solución se gestionan desde el panel de ayudas de la plataforma. La solución privada no forma parte de los archivos publicados por el servicio.

## Publicación del lote

El script actualiza explícitamente WEB-02, WEB-06, FOR-05 y DFIR-01 y enriquece ESC-07 mediante el catálogo HTTP. Preserva sus códigos, flags configuradas, puntuaciones e historial. Una configuración que deba cambiar se rechaza si conserva corridas activas; cerrarlas por el flujo habitual antes de aplicar. La repetición no duplica flags ni asignaciones.

Ensayo con rollback, después de desplegar el código:

```powershell
Get-Content backend/configure_vm_logic_catalog.py | docker compose exec -T api python - --group 45HY
```

Aplicación explícita al grupo verde:

```powershell
Get-Content backend/configure_vm_logic_catalog.py | docker compose exec -T api python - --apply --group 45HY
```

Después de cambiar referencias, usar la sincronización habitual de Guacamole para los grupos afectados. Los scripts anteriores de catálogo offline/VM preservan los escenarios `VM-LOGIC-*`, evitando que una ejecución posterior los convierta de nuevo.

## Contrato e implementación

Los cuatro casos nuevos usan `workspace_strategy=vm_logic_lab`, escenarios `VM-LOGIC-CODIGO` y referencias `LAB-KALI`/`LAB-LNXVICT`. ESC-07 mantiene `http_files_lab` y su ciclo HTTP existente.

`GET /api/v1/runs/ID/vm-logic` devuelve solo URL inicial, objetivo y contrato de respuesta. `POST /api/v1/runs/ID/vm-logic/answer` valida los resultados y devuelve la flag únicamente tras una respuesta correcta. Ambos comprueban propietario, grupo activo asignado, publicación, estrategia y vigencia. Las rutas antiguas offline/DFIR no sirven estos casos debido a su estrategia distinta.

`vm_logic.case_for(run, code)` genera evidencia y respuesta privada de manera reproducible por usuario y corrida. `prepare` publica el registro en la víctima; `cleanup` elimina únicamente el registro identificado por esa corrida. Los hooks no reservan el servicio exclusivo del puerto 18081.

El servicio HTTP v2 publica exclusivamente entradas generadas y rutas explícitas del registro, sin resolver rutas HTTP hacia archivos del sistema. Rechaza traversals, aliases codificados, queries y métodos no admitidos. Los datos didácticos solo se sirven a Kali. La propia víctima puede consultar una ruta de disponibilidad que solo devuelve `Ready` y la versión, sin evidencia.

La publicación usa SFTP y permisos privados con el usuario de inyección existente, sin modificar sudo, OpenSSH ni usuarios del sistema. Un cambio del código del servicio reinicia únicamente el proceso propio que coincide exactamente con el ejecutable y directorio esperados; los registros de otras corridas se conservan. La comprobación de disponibilidad exige versión v2 y registro vigente, en lugar de comprobar solo que el puerto acepta TCP.

Kali sigue siendo compartida: una carpeta por corrida organiza el trabajo y no equivale a aislamiento entre alumnos que usan la misma cuenta del sistema.

## Pruebas del lote

Se verificaron catorce pruebas locales: autenticación HTTP Basic previa, descubrimiento/correlación de respaldos, variación reproducible por corrida, ausencia de evidencias en metadatos, bypass POST real, autorización de objetos, adquisición y hashes de todos los artefactos, correlación DFIR con calibración, caducidad, eliminación y restricciones de rutas/estrategias.

Aceptación técnica del 15 de octubre de 2026, después del despliegue y aplicación de los catálogos: WEB-02, WEB-06, FOR-05 y DFIR-01 completaron adquisición HTTP desde Kali hacia LNX-VICT, resolución a partir de recursos públicos, validación, puntuación una sola vez, cierre y revocación. Se comprobó el catálogo idempotente y el rollback de PostgreSQL, sin usuarios ni puntos QA persistidos.

La integración HTTP de la misma versión comprobó ESC-06 con Hydra y HTTP Basic reales desde Kali, y ESC-07 con descubrimiento, respaldos señuelo, comprobación SHA-256 y reconstrucción de fragmentos. Ambos completaron validación, puntuación única y revocación, con catálogo idempotente y rollback de los datos QA.

La aceptación visual del 15 de octubre de 2026 comprobó WEB-02 con la sesión del estudiante: contador de una hora, 100 puntos disponibles, pistas secuenciales y terminal Kali integrada respondiendo a `pwd`. RDP mostró el escritorio completo, centrado y sin contraseña de desbloqueo, también al alternar pantalla completa. No se solicitaron pistas ni se enviaron respuestas del alumno durante esta comprobación.

La comparación anterior y posterior al despliegue conservó los once resultados existentes y todos sus puntajes, sin registros de prueba persistidos. El login se comprobó con el título, logo y texto centrados.
