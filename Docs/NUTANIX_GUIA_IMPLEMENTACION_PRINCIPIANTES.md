# CoCiber CTF: instalación y habilitación de los dos ejercicios (principiantes)

> **Estado de este cambio:** inventario y prueba TCP SSH/RDP integrados en la rama. **No se ha probado todavía desde la red Nutanix ni se ha habilitado la restauración automática de snapshots.** No publicar los retos como operativos sin seguir la validación.

## 1. Antes de comenzar

Debes tener una cuenta administradora de Cociber, acceso al Guacamole existente y autorización del administrador de Nutanix. **No borres VMs, snapshots, datos de PostgreSQL ni secretos del archivo `.env`.** Confirma por escrito con infraestructura las ACL entre VLAN 20 (atacantes), VLAN 30 (víctimas), servidor web/API y Guacamole (guacd).

| Máquina | IP | Rol |
| --- | --- | --- |
| LAB-KALI | 10.10.20.10 | Atacante; máximo seis sesiones concurrentes según infraestructura |
| LAB-KALI-PURPLE | 10.10.20.11 | Atacante; máximo seis sesiones |
| LAB-KALI-BLUE | 10.10.20.12 | Atacante; máximo seis sesiones |
| LAB-WINVICT-A | 10.10.30.10 | Víctima |
| LAB-WINVICT-B | 10.10.30.11 | Víctima |
| LAB-LNXVICT | 10.10.30.12 | Víctima SSH |
| LAB-SRVWEB | 10.10.30.20 | Víctima web |
| LAB-SRVFSAD | 10.10.30.21 | Víctima |

**Atención:** la VLAN de atacantes es `10.10.20.0/24`, no `10.10.30.20/24`. Los nombres/puertos de aplicaciones web deben comprobarse en la VM antes de registrarlos. El directorio `labs/operacion-condor` conserva una copia histórica; la versión actual también se mantiene en un repositorio independiente. **No se encontró** `33_Fase5_App_Vulnerable_LAB_SRVWEB` en este repositorio; facilitar esa guía para una integración fiel.

## 2. Actualizar sin destruir producción

1. Realiza copia verificable del código y respaldo de PostgreSQL/Redis con los procedimientos habituales. Conserva un punto de restauración.
2. Revisa y fusiona la rama de cambios después de ejecutar pruebas. El servidor de producción utiliza **solo** `docker-compose.prod.yml`.
3. En la carpeta del servidor (tras actualizar el código, manteniendo su `.env` privado), ejecuta:

```bash
sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml build api web
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps api python -m app.check_services
sudo docker compose -f docker-compose.prod.yml up -d --no-deps api web
sudo docker compose -f docker-compose.prod.yml ps
```

Si algún paso falla, detente. **Nunca uses `down -v`** en esta operación. No cambies la base de datos de Guacamole.

## 3. Registrar las conexiones

En Administración > Guacamole, crea una conexión SSH o RDP usando el nombre/IP de la tabla. Puerto SSH habitual: 22; RDP: 3389. La práctica SSH restringida utiliza **2222** solo después de instalar el servicio didáctico específico. Guarda credenciales en el gestor de secretos autorizado, no en Markdown.

Pulsa **Verificar conexión**: la API intenta abrir un socket únicamente a IPs autorizadas; si el puerto responde, aparece el portal Guacamole en otra ventana. Allí comprueba manualmente que se abre una sesión real y que se puede interactuar. La ventana nueva no demuestra autenticación: anota el resultado en la ficha del laboratorio y asigna permisos al grupo solo después de confirmar.

## 4. Ejercicio 2: fuerza bruta SSH (dificultad media, 250 puntos)

El código existente `ESC-02-BRUTEFORCE` genera usuario temporal `ctf<ID>`, contraseña seleccionada entre 12 candidatas y una **flag por corrida** en el servicio didáctico SSH, puerto 2222. Se conecta a `LAB-LNXVICT` (`10.10.30.12`). **No prueba ni modifica contraseñas administrativas del sistema**.

Antes de habilitarlo, comprueba:
1. Acceso administrativo SSH autorizado desde la API a la VM, claves conocidas y permisos correctos del usuario inyector.
2. Que la VM Linux contiene `python3`, que el usuario inyector puede ejecutar el servicio restringido y que TCP/2222 es alcanzable **solo desde la zona atacante**.
3. Que la rutina de preparación y limpieza inicia/detiene registros de usuario temporal, incluso al caducar la corrida.
4. Que se pueden iniciar dos corridas independientes sin revelar entre sí las flags y que el snapshot base no contiene credenciales de práctica activas.
5. Que `ESC-02-BRUTEFORCE` mantiene **una única flag dinámica activa** y está asignado exclusivamente a los grupos de formación autorizados.

El catálogo `backend/configure_vm_catalog.py` modifica retos **ya existentes**: revisa su efecto en una copia de la BD, nunca lo ejecutes a ciegas en producción.

## 5. Ejercicio 3: explotación web (dificultad media, 250 puntos iniciales)

La VM `LAB-SRVWEB` tiene IP `10.10.30.20`. Identifica primero desde Kali el puerto autorizado de **Operación Cóndor** y de la segunda aplicación vulnerable. No asumas que usan el mismo puerto ni que corresponden a la misma instalación.

La versión actualmente documentada de `WEB-CONDOR` emplea una bandera **estática de la instalación compartida**. El código de este cambio **no la convierte automáticamente en dinámica**. Para cumplir el requisito de banderas únicas, hace falta modificar el servicio de LAB-SRVWEB o desplegar instancias aisladas por grupo/corrida con una verificación firmada vinculada al `run_id`. Mientras eso no exista, anuncia durante la presentación que es un **reto web compartido de prueba**, no una flag única por alumno.

No publiques la segunda aplicación vulnerable hasta contrastar sus rutas, credenciales de demostración, límites de carga, método de obtención de flag y restauración según `33_Fase5_App_Vulnerable_LAB_SRVWEB`.

## 6. Snapshots Nutanix AHV

El administrador de Nutanix debe aprobar los UUID de VMs, snapshots base y permisos de Prism/AHV. Secuencia prevista: **reservar VM o pool -> restaurar snapshot base -> comprobar servicios -> inyectar flag de corrida -> ejecutar -> retirar flag -> restaurar -> liberar**. La restauración automática **no está implementada en este cambio**. Si las VMs son compartidas por seis sesiones, **no restaures una VM durante sesiones activas**: usa clones/pools aislados o sincroniza el calendario de reinicios. Solicita validación de identidad de las VMs y respaldo antes de cualquier automatización.

## 7. Publicar el reto

Solamente tras comprobar login real en Guacamole, apertura desde Kali, generación y envío de la flag, cierre y restauración sin pérdidas. Registra resultado con fecha y evidencia, publica para un grupo piloto y repite para una segunda sesión. Consulta la guía de validación adjunta.
