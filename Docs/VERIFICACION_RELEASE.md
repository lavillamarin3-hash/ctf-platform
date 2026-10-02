# Verificación de la entrega

Esta entrega conserva el esquema PostgreSQL existente. No ejecutar migraciones, restauraciones de SQL ni reinicializar volúmenes para aplicar estos cambios.

## Resultados del 30 de septiembre de 2026

| Verificación | Resultado | Alcance |
|---|---|---|
| Backend y compilación Python | 90 pruebas PASS; `compileall` PASS | Flags dinámicas/estáticas, ruta opcional por código, lifecycle y rollback, autorización SSH/RDP por VM, tickets, visibilidad/asignación, ranking. Dobles de infraestructura y SQLite efímero; sin PostgreSQL/SSH/Redis de producción. |
| Helpers frontend | 25 comprobaciones PASS | 8 de recursos seguros, 6 de cambios editoriales de flags, 6 de visibilidad de cleanup pendiente y 5 de notificaciones sin datos sensibles. |
| Navegador | 15 comprobaciones PASS | 13 del estudiante y 2 de edición de recursos por administrador, con API/WS aislados. Incluye SSH/RDP alternables, fullscreen terminal, campana y ejecución expirada pendiente de limpieza. |
| TypeScript y Vite | PASS | Compilación del código actualizado; también se verificó instalación aislada con el `package-lock.json` exacto, 134 paquetes. |
| Responsive y tipografía | 7 comprobaciones de lista/LAB PASS y verificación de selector | Lista a 1440/768/390 px en temas claro/oscuro: sin overflow horizontal; escala general 90% persiste; fullscreen LAB y fullscreen de conexión a 1440/390; zoom 75-200%; flag ficticia larga envuelta; sin resize repetido en reposo del fixture. |
| Configuración Compose | PASS | Validación silenciosa sin mostrar secretos resueltos. |
| Dependencias Python | PASS | Los rangos declarados admiten las versiones verificadas; resolución offline de `requirements.txt` y `pip check` aprobados. |
| Imágenes Docker | BLOQUEADO | Los intentos de `docker compose build api web` fallaron por acceso denegado a configuración/buildx/daemon local; no se construyeron imágenes. |
| Guacamole real: lectura | PASS limitado | Biblioteca pública de la instalación y consultas de autenticación de servicio/conexiones SSH en modo lectura. Esto no demuestra una sesión SSH personal del estudiante. |
| Flujo físico completo | PENDIENTE | Túnel personal, comandos SSH/RDP reales, inyección física, limpieza de VM/Redis y segunda flag requieren aceptación en el laboratorio autorizado. |

Los resultados de navegador usan la biblioteca oficial obtenida de Guacamole; el protocolo y las respuestas de API son fixtures. Un badge «Conectada» en estas capturas no certifica un comando, un escritorio RDP ni una VM real. No se simula la implementación interna de `Guacamole.Client`. El montaje estable del viewport, un solo cliente a la vez y la ausencia de `sendSize` repetidos en reposo reducen causas plausibles de parpadeo; solo la prueba SSH física puede confirmar que desapareció en la instalación del usuario.

## Pruebas reproducibles

Desde `backend`, con las dependencias de `requirements.txt` instaladas:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app tests
```

Desde `frontend`:

```powershell
npm ci
npm run build
node tests/challenge-resources.cjs
node tests/challenge-flag-changes.cjs
node tests/laboratory-run-state.cjs
node --test tests/notifications.test.mjs
npm run preview -- --host 127.0.0.1 --port 4183 --strictPort
```

El script `scripts/qa/browser-smoke.cjs` necesita Playwright, un navegador Chrome instalado y el cliente JavaScript oficial de la instalación Guacamole. Descargar únicamente la biblioteca pública `guacamole-common-js/all.min.js` de la instalación autorizada, sin credenciales ni tokens, y guardarla como `work/qa/guacamole-common-js.js`. Se ejecuta en otra consola desde la raíz:

```powershell
node scripts/qa/browser-smoke.cjs --url http://127.0.0.1:4183 --guacamole-library work/qa/guacamole-common-js.js --artifacts work/qa/browser
node scripts/qa/admin-resource-smoke.cjs --url http://127.0.0.1:4183 --artifacts work/qa/admin-resources
```

Si Playwright está disponible en un runtime externo, definir `QA_PLAYWRIGHT_MODULE` con la ruta al módulo antes de ejecutar los scripts. Los resultados JSON y capturas quedan en los directorios indicados. También puede usarse pnpm para ejecutar el build/preview; `npm ci` es la verificación de instalación reproducible del Dockerfile. Nunca usar los fixtures como comprobación de una VM real: interceptan las solicitudes API y WebSocket, utilizan datos de prueba y no contactan PostgreSQL, Redis, SSH ni Guacamole.

La prueba de navegador cubre búsqueda/filtros, enlaces/material de apoyo opcional, inicio/reutilización, autenticación personal, selector SSH/RDP con un cliente a la vez, fullscreen de terminal, transporte del cliente oficial con protocolo de prueba, teclado, portapapeles, notas, flags correcta/incorrecta, avisos sin guardar flag, cierre fallido/reintento, segunda ejecución y responsive claro/oscuro. La regresión visual adicional cubre lista, pantalla completa LAB, zoom, preferencia tipográfica y flag ficticia larga. Para una ejecución `expired` con conexión aún activa confirma que Mis conexiones y el detalle conservan el botón de cierre/reintento, bloquean nuevos envíos y mantienen notas hasta confirmar la limpieza. No fabrica salida de comandos Linux ni verifica reproducción de videos externos.

La regresión administrativa añade video/presentación e instrucciones, verifica que no haya solicitudes de mutación de flags y comprueba la reapertura del material guardado con sus metadatos de flags existentes intactos.

## Comprobación Docker

Desde la raíz, sin iniciar servicios ni modificar datos:

```powershell
docker compose config --quiet
docker compose build api web
```

`config --quiet` comprueba la configuración sin mostrar variables resueltas. No adjuntar `docker compose config` completo, archivos `.env` ni logs con tokens o credenciales a un reporte.

En el entorno de edición Windows, el CLI Docker 29.7.2 y Compose v5.4.0 están presentes, pero el acceso al pipe `docker_engine` está denegado. La validación de sintaxis Compose pasó; la construcción de imágenes requiere repetir el comando en un entorno con acceso al daemon. Si no hay internet, hacen falta imágenes base y dependencias ya cacheadas o un paquete de imágenes preparado de antemano. Nutanix/Prism no es un servicio definido en Compose y su ausencia no debería impedir servir la web. Una compilación Vite exitosa no equivale a una construcción Docker exitosa.

## Aceptación física en el laboratorio autorizado

La aceptación final requiere una cuenta de estudiante de prueba con LAB-01 asignado, una VM controlada y el Guacamole real configurado. Registrar el resultado de cada comprobación sin copiar valores de flags ni secretos al reporte.

| Paso | Evidencia necesaria |
|---|---|
| Asignación | El estudiante ve únicamente sus retos/laboratorios; otro estudiante no puede consultar ni abrir su ejecución. |
| Iniciar y reutilizar | Se crea una ejecución/instancia activa; repetir la apertura reutiliza esa instancia. |
| Generar e inyectar | La evidencia aparece físicamente en la VM preparada y el backend almacena solamente el hash correspondiente a la ejecución. |
| Abrir terminal | El cliente integrado recibe el túnel autorizado y ejecuta un comando inocuo en la VM real, sin login administrativo en el navegador. |
| Elegir RDP, si existe | Guacamole muestra solo el escritorio de la VM reservada, con permiso READ del estudiante; alternar a SSH cierra el cliente RDP sin duplicarlo. No activar el botón si RDP no está configurado. |
| Encontrar y copiar | Leer la evidencia del laboratorio, copiar la selección de terminal y pegarla en el candidato sin transcribirla. |
| Incorrecta/correcta | La respuesta incorrecta se rechaza y la correcta se acepta en backend; los puntos se otorgan una sola vez. |
| Cerrar | El túnel se revoca; la ejecución se cierra tras confirmar limpieza; un fallo conserva la instancia para reintento. |
| Limpieza | Confirmar ausencia de la evidencia en la VM y liberación de las claves Redis de la ejecución/instancia. |
| Segunda corrida | Iniciar otra ejecución, confirmar evidencia diferente y rechazo de la flag anterior. |
| Piloto RECON-02 | Solo después de prepararlo según `10_Retos_Iniciales_CTF.md`: escanear la IP de la VM asignada en red aislada, descubrir el puerto HTTP, leer la evidencia inyectada, cerrar y confirmar que la URL deja de servirla. |

No sustituir estas comprobaciones con pruebas unitarias, respuestas de fixtures ni capturas de un panel con estado «Conectado».

## Paquete y trazabilidad

El paquete de entrega debe incluir fuente, tests y documentación; excluir `.env`, `.env.backup`, volcados SQL de datos, `.git`, `node_modules`, cachés y artefactos de trabajo. Mantener la configuración privada existente del despliegue. Usar un commit local revisable y un archivo construido desde archivos versionados; confirmar `git status --short` vacío antes de publicar el paquete. Conservar la referencia del commit anterior para revertir código sin restaurar ni borrar datos.
