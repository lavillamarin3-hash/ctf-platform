# Reapertura del laboratorio y escenarios con las dos VMs actuales

## Diagnóstico confirmado el 1 de octubre de 2026

El build Docker de `api` y `web` terminó correctamente en la instalación del administrador. El registro operativo compartido muestra `LAB-LNXVICT` lista en PostgreSQL (`192.168.146.137`, laboratorio `LAB-VICTIMAS`), una fila `challenge_instances` disponible y una reserva Redis temporal cuyo identificador `167` no existía en `challenge_runs`. Esa reserva caducó sin borrado manual. Un siguiente intento también falló. Desde el contenedor API, la prueba TCP al puerto SSH devolvió inicialmente `11`: la VM víctima estaba apagada. **El administrador la encendió y confirmó después `SSH=0` desde el contenedor API, una nueva reserva Redis tras el intento fallido y una conexión SSH presente en Guacamole.** Por tanto, el puerto cerrado ya no explica el fallo actual: la ejecución se detiene después de adquirir la reserva. Aún no se ha identificado la etapa exacta ni confirmado una reapertura completa.

El laboratorio administrativo llamado `LAB-01` con cero VMs no es, por sí solo, el destino del reto: el backend resuelve la VM por las referencias del reto y la víctima se encuentra en `LAB-VICTIMAS`. Tampoco basta con que PostgreSQL diga `ready`: debe existir conectividad real desde el contenedor API.

### Recuperación segura, sin borrar Redis ni datos

1. Comprueba que la VM víctima sigue encendida, conserva `192.168.146.137`, tiene `sshd` escuchando en el puerto 22 y que la red/firewall permiten el acceso desde Docker. En la consola local de la VM, si está disponible: `ip -br addr`, `sudo systemctl is-active ssh`, `sudo ss -lntp | grep ':22'`. No copies contraseñas ni flags al informe.
2. Repite desde el proyecto: `docker compose exec api python -c "import socket; s=socket.socket(); s.settimeout(3); print(s.connect_ex(('192.168.146.137',22))); s.close()"`. Debe imprimir `0`. Un valor distinto significa que todavía no se puede preparar el reto dinámico.
3. En Administración → Laboratorios / VMs, pulsa **Diagnosticar LAB-01**. El panel muestra inventario, pool, Guacamole, puerto SSH, si el inyector logra autenticarse con la configuración de la API y la reserva Redis (solo presencia/TTL, nunca su valor). La prueba de autenticación ejecuta `true` y no cambia la VM. Si la autenticación falla, el instructor revisa dentro de su entorno las credenciales del inyector, la clave de host y la cuenta SSH; no las envíes por chat ni hagas capturas de `.env`.
4. Verifica que `docker exec ctf_project-redis-1 redis-cli GET "ctf:lab:reservation:192.168.146.137"` devuelve `(nil)` y que no hay otra corrida activa sobre esa VM antes de reintentar. Una reserva tras un fallo puede conservarse hasta su TTL para evitar reutilizar una VM que aún contenga evidencia. No uses `DEL`, `FLUSHDB`, `down -v` ni edites `challenge_instances` directamente.
5. Prueba con **un** estudiante. Cierra y confirma la limpieza antes de probar con el siguiente. La VM víctima es compartida y no admite dos corridas dinámicas simultáneas.
6. Si vuelve a fallar, el backend actualizado distingue reserva, permisos Guacamole e inyección SSH; su log registra únicamente la etapa y el tipo de excepción, sin credenciales, IP, token ni flag. Con el proyecto actualizado, comparte solo el aviso visible al estudiante, los indicadores del panel y una línea `etapa=... tipo=...` del log API. No compartas el valor de la flag ni el contenido de variables de entorno.

El backend actualizado comprueba TCP/SSH antes de crear el run o reservar Redis. El diagnóstico comprueba por separado la autenticación real del inyector; tampoco garantiza que el script remoto exista o tenga permisos `sudo -n`. Esta separación localiza el punto de fallo sin exponer secretos. No se fuerza la liberación de una reserva ajena.

## Novedad de las capturas: LAB-01 sin VM y `lab02` aparente

El **reto** `LAB-01` y el **laboratorio** de inventario llamado `LAB-01` son entidades distintas. La VM física de ese reto es `LAB-LNXVICT` en `LAB-VICTIMAS`; no hace falta copiarla al laboratorio homónimo. En la captura, `lab02` aparece como «Kali Linux» con la IP víctima `.137`: son metadatos incompatibles. La versión anterior de la interfaz podía mostrar un guardado solo en el navegador aun cuando el API rechazaba la IP duplicada; por eso una recarga podía volver a mostrar cero VMs. Esto es una **hipótesis fundada en el código**, no prueba de que `lab02` exista en PostgreSQL. El controlador nuevo usa siempre el inventario del API y no anuncia un guardado que este haya rechazado. Además, LAB-01 ahora selecciona solo una ficha `LAB-LNXVICT` Linux, `ready`, con IP `.137`; si falta o está duplicada, falla de forma segura. El diagnóstico administrativo advierte si varias fichas registradas usan la IP víctima. No se eliminó `lab02` ni ninguna fila automáticamente.

## Si una cuenta se borró solo en Guacamole

«Eliminar solo Guacamole» nunca eliminó el usuario CTF. Desde esta versión, el panel remoto bloquea el borrado de cuentas compartidas y ofrece «Gestionar en CTF». Para Kevin, abre **Administración → Gestionar usuarios / Usuarios y roles**. Si tiene corridas, puntuación, envíos, asignaciones o auditoría, no se borran esos datos: usa **Deshabilitar** para impedir nuevos accesos. Si no tiene referencias, el borrado CTF puede terminar incluso si su cuenta Guacamole ya no existe. El API comprueba dependencias SQL antes de intentar borrar la cuenta remota y muestra un conflicto legible cuando conservar el historial es obligatorio. Ninguna cuenta real se modificó durante la preparación de esta entrega.

## Inventario operativo de esta fase

El administrador confirmó solamente estas dos IP disponibles:

| Rol | VM | IP | Estado de uso |
| --- | --- | --- | --- |
| Atacante | `LAB-KALI` | `192.168.146.134` | Confirmada por el administrador; comprobar Guacamole y red antes de publicar retos |
| Víctima | `LAB-LNXVICT` | `192.168.146.137` | Registrada; SSH desde API ya responde, falta validar inyección/cierre |

La vista administrativa muestra por defecto solo laboratorios que contienen las fichas exactas `LAB-KALI` y `LAB-LNXVICT` con estas IPs y estado `ready`, y permite consultar el inventario completo. La vista del estudiante omite VMs con otro nombre/IP o estado distinto de `ready`. Los datos de PostgreSQL **no se borran**; las otras VMs pueden recuperarse cuando existan. En nuevas instalaciones, el seed de demostración solo propone estas dos. Los retos ya publicados que dependan de VMs ausentes deben quedar sin asignar o despublicarse por decisión del instructor; ocultar inventario no crea ni repara máquinas.

## Cinco escenarios del documento adjunto, adaptados a la realidad

El documento `25_CTF_Inyeccion_Dinamica_Flags_Por_Escenario.md` es una propuesta de diseño, no una descripción de VMs ya desplegadas. Sus IP `10.10.30.x`, WinRM, Samba, app web vulnerable, Security Onion y snapshots no están verificados en esta instalación. No se agrega la tabla `scenario_sessions`: el esquema actual ya dispone de `challenge_runs`, `challenge_run_flags`, `challenge_instances` y reserva Redis, preservando la prohibición de migrar PostgreSQL.

| Escenario | Con dos VMs actuales | Evidencia de red / límite |
| --- | --- | --- |
| 1. Reconocimiento (`T1046`) | **Piloto viable** tras recuperar SSH, habilitar acceso de estudiante a Kali y desplegar un servicio didáctico en LNXVICT | Un escaneo genera flujos observables si el mirror realmente recibe esos puertos; la alerta depende de las reglas del sensor. |
| 2. Intentos de acceso SSH (`T1110.001`) | **Condicional**: usar solo una cuenta de prueba y pocos intentos acotados en LNXVICT | El mirror ve sesiones/conexiones, pero SSH cifra el resultado de autenticación; los fallos se confirman con logs del host, no solo con la captura de red. |
| 3. Aplicación web (`T1190`) | **Pendiente**: `SRV-WEB` no existe hoy; podría montarse una app deliberadamente vulnerable y aislada en LNXVICT tras revisión | Si usa HTTPS, el mirror no ve el payload sin terminación/telemetría adicional. No afirmar detección antes de probar reglas. |
| 4. Movimiento lateral SMB (`T1021.002`) | **No ejecutable**: faltan las dos VMs Windows y su red/SMB | No habilitar WinRM ni recursos administrativos por un escenario todavía no desplegado. |
| 5. Exfiltración simulada (`T1048`) | **Condicional**: transferencia de un archivo de prueba inocuo de LNXVICT a Kali, con servicio receptor aislado | El mirror puede observar flujo y volumen, no necesariamente contenido si el protocolo va cifrado. |

La ausencia de Nutanix/snapshots implica que cerrar un run limpia la flag dinámica, pero **no restaura automáticamente** los cambios que un alumno haga en una VM. Antes de permitir explotación real, define una VM desechable o una restauración manual verificada. No se ejecutó ningún ataque ni se configuró un sensor durante esta entrega.

## Reto piloto para administrador: atacante Kali → víctima Linux

**Borrador, no publicado.** El catálogo de código incluye `ESC-01-RECON` para instalaciones nuevas con seed de demostración habilitado; no modifica la base existente porque esta entrega no activa seeds ni hace escrituras de administración. Si no aparece en Administración → Retos, créalo como borrador con estos datos: nombre «Descubre el servicio de evidencia», nivel Básico, categoría MISC, MITRE `T1046`, 100 puntos y referencia de víctima `LAB-LNXVICT`. Objetivo: desde `LAB-KALI` (`192.168.146.134`), descubrir un puerto didáctico en `LAB-LNXVICT` (`192.168.146.137`) y leer una flag dinámica que el backend haya escrito **solo en la víctima**. El instructor configura la flag dinámica con plantilla `FLAG{esc-01_{{USER}}_{{RUN_ID}}_{{RAND}}}`; nunca publica su valor en el frontend. El servicio didáctico debe escuchar únicamente en la red autorizada, servir la evidencia al comenzar la corrida y devolver 404 tras el cierre. Para la primera aceptación, usar un puerto dedicado como `18081` y tráfico inofensivo; no reutilizar servicios de producción.

**Condiciones antes de crearlo/publicarlo:** (a) SSH API→LNXVICT responde `0` y la inyección/limpieza de LAB-01 funciona; (b) Kali y LNXVICT se alcanzan entre sí, y el estudiante tiene conexión Guacamole personal a Kali; (c) el instructor despliega el servicio didáctico en la víctima, restringido a la red de laboratorio; (d) se comprueba que el estudiante no obtiene una vía directa a la flag a través de la terminal de la víctima. El flujo actual de run integra la terminal de la VM reservada (víctima), **no una segunda terminal atacante**; por ello este reto se entrega como diseño verificable y no se debe publicar como ejercicio atacante→víctima hasta integrar esa selección dual con autorización y limpieza correctas.

En la aceptación futura, el alumno usará únicamente `192.168.146.137`, con un escaneo pequeño de puertos autorizados, por ejemplo `nmap -sT -Pn -p 22,18081 192.168.146.137`, y recuperará la evidencia del servicio de práctica. Después validará la flag en la plataforma y cerrará el run. Registrar también si el sensor vio el tráfico; no prometer una alerta que no se haya observado.

No copies del documento propuesto comandos que colocan flags/contraseñas en argumentos de shell, `pkill` amplio, `TrustedHosts` de toda una subred ni instrucciones que añadan tablas nuevas. La inyección actual usa un adaptador SSH existente y tiene límites de aislamiento documentados; un despliegue multiusuario exigirá endurecerlo y verificarlo físicamente.
