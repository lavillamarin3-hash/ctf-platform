# 01. Empieza aquí: orden de ejecución

Actualización: **10 de noviembre de 2026**. La plataforma nueva está desplegada, conecta a PostgreSQL/Redis y un jugador ya puede iniciar un reto y abrir SSH en la Kali. No repitas instalaciones ya verificadas: continúa con [05. Modales y usuarios](../01_Plataforma/05_MODALES_Y_GESTION_USUARIOS.md) y [09. Windows y FTP](../02_Laboratorios/09_PREPARACION_WINDOWS_Y_FTP.md). El recorrido inicial se conserva debajo para instalaciones aún no preparadas.

**Ruta observada en LAB-CTFWEB: `/home/lab-ctfweb/ctf-platform`.** Las primeras guías usaban la ruta nominal `/ctf-plataform/`: donde aparezca, usa el checkout real comprobado con `pwd -P` y los archivos `.env.fresh` y `deploy/docker-compose.fresh.yml`. No crees otra carpeta ni reinstales el worker con el directorio antiguo.

## Cambios del 12 de noviembre

- Si falla el escritorio remoto: [06. Diagnóstico RDP de Guacamole](../01_Plataforma/06_DIAGNOSTICO_RDP_GUACAMOLE.md).
- Para el fallo confirmado de LAB-KALI-BLUE con Guacamole Docker 1.6.0: [08. Diagnóstico específico](../01_Plataforma/08_KALI_BLUE_RDP_DOCKER.md).
- Para actualizar y usar el nuevo recorrido: [07. Preparación de retos y login](../01_Plataforma/07_PREPARACION_RETOS_Y_LOGIN.md).

## Cómo utilizar las guías

1. Lee [02. Acceso y comandos base](02_ACCESO_Y_COMANDOS_BASE.md). Explica cómo abrir la terminal correcta, conectarte, cambiar de carpeta, editar y salir.
2. Sigue la tabla en orden. Cada fila indica el equipo donde ejecutar los comandos y el resultado necesario antes de continuar.
3. Copia únicamente el contenido de un bloque de comandos, sin los delimitadores Markdown. Ejecuta un bloque, revisa su resultado y después pasa al siguiente.
4. Un comando que termina con error no cuenta como paso completado. Conserva el mensaje y consulta la sección de diagnóstico o al responsable del laboratorio.

## Recorrido para la plataforma que ya funciona

| Orden | Guía | Equipo | Resultado antes de avanzar |
| --- | --- | --- | --- |
| 1 | [Acceso y comandos base](02_ACCESO_Y_COMANDOS_BASE.md) | Equipo local y servidor web | Sabes identificar dónde estás y entrar al checkout real |
| 2 | [Verificar plataforma existente](../01_Plataforma/01_VERIFICAR_PLATAFORMA_EXISTENTE.md) | LAB-CTFWEB | API/web activos y acceso a BD correcto |
| 3 | [Actualizar interfaz y Guacamole](../01_Plataforma/02_ACTUALIZAR_INTERFAZ_Y_GUACAMOLE.md) | LAB-CTFWEB y navegador | Versión actualizada; omitir reconstrucción si ya está aplicada |
| 4 | [Comprobar Guacamole y acceso a Kali](../01_Plataforma/03_GUACAMOLE_Y_CONEXIONES.md) | Navegador y Kali | Inventario remoto consultado y acceso de administración verificado |
| 5 | [Inventario y catálogo](../01_Plataforma/04_INVENTARIO_Y_CATALOGO.md) | LAB-CTFWEB | Fichas y cinco borradores; aún sin publicar |
| 6 | [Requisitos y transferencia](../02_Laboratorios/01_REQUISITOS_Y_TRANSFERENCIA.md) | LAB-CTFWEB y VM | Archivos disponibles; snapshots y cuentas de mantenimiento identificados |
| 7 | [Cuenta técnica y claves](../02_Laboratorios/02_CUENTA_TECNICA_Y_CLAVES.md) | LAB-CTFWEB y VM | `labops` autentica por clave en cada VM elegida |
| 8 | [LNXVICT: SSH didáctico](../02_Laboratorios/03_LNXVICT_SSH.md) | LAB-LNXVICT | Servicio 2222 y helper correctos |
| 9 | [Kali: sesiones temporales](../02_Laboratorios/04_KALI_SESIONES.md) | Cada Kali que se utilizará | Helper y SSH de cuentas de práctica preparados |
| 10 | [SRVWEB: DVWA](../02_Laboratorios/05_SRVWEB_DVWA.md) | LAB-SRVWEB | Tabla compatible, helper y acceso de DVWA comprobados |
| 11 | [Pruebas y worker](../02_Laboratorios/06_PRUEBAS_Y_WORKER.md) | LAB-CTFWEB | Pruebas de inyección correctas; worker supervisado |
| 12 | [Grupos, retos y piloto](../02_Laboratorios/07_GRUPOS_RETOS_Y_PILOTO.md) | Navegador | Piloto aprobado, grupo asignado y reto publicado |
| 13 | [Demostración del jugador](../02_Laboratorios/08_DEMO_JUGADORES.md) | Navegador y Kali | Práctica completada y limpieza comprobada |

Puedes preparar primero ESC-02: completa los pasos comunes, LNXVICT y al menos una Kali. Deja ESC-03 deshabilitado hasta terminar también SRVWEB y el acceso al navegador de Kali. Nunca marques una VM disponible únicamente porque aparezca en un listado.

## Documentación que no se ejecuta como parte de ese recorrido

| Carpeta | Cuándo utilizarla |
| --- | --- |
| [DocumentacionBD](../DocumentacionBD/01_CREDENCIALES_Y_PREPARACION.md) | Instalación de datos o reinicio deliberado con respaldo. **No repetir limpieza ahora que la BD funciona.** |
| [03_Operacion](../03_Operacion/01_RESTAURACION_SNAPSHOTS.md) | Restauraciones, respaldos y actualizaciones posteriores |
| [04_Pendientes](../04_Pendientes/01_ESTADO_Y_ENTREGABLES.md) | Preparar información de ESC-01/04/05; siguen deshabilitados |
| [05_Referencia](../05_Referencia/01_INSTALACION_DESDE_CERO.md) | Arquitectura, instalación desde cero, esquema y pruebas de desarrollo |
| [90_Historico](../90_Historico/00_INDICE_HISTORICO.md) | Consultar la versión anterior; sus instrucciones no se aplican al despliegue fresh |

Los documentos de `labs/demo-vulnerable` y `labs/operacion-condor` son paquetes opcionales distintos. No se necesitan para los dos escenarios de este recorrido.

## Quién realiza cada parte

- **Operador de plataforma:** SSH a LAB-CTFWEB, actualización de contenedores, configuración privada y worker.
- **Administrador de VM/Nutanix:** snapshots, instalación de helpers y permisos en las VM.
- **Administrador web:** crear, editar, desactivar o eliminar usuarios y asignar los tres roles no administrativos.
- **Instructor:** consultar jugadores, gestionar grupos, pilotos, publicación y demostración.
- **Jugador:** únicamente la práctica asignada desde Kali y el envío de su bandera.

Una persona puede tener varios roles, pero las cuentas Linux, el administrador web, las cuentas de los motores y los usuarios de Guacamole son diferentes. No sustituyas una por otra.
