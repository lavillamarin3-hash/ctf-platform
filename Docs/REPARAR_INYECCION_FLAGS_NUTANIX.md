# CoCiber CTF · Resolver error de inyección dinámica en Nutanix

**Fecha:** 28-10-2026. **Objetivo:** permitir que el estudiante inicie el reto con su bandera real, sin modificar contraseñas, registros ni VMs ajenas.  
**Instalaciones:** `10.10.10.13` = app Docker; `10.10.30.12` = LAB-LNXVICT; `10.10.20.10` = LAB-KALI; `10.10.30.20` = LAB-SRVWEB.

**Ningún cambio de GitHub instala automáticamente componentes dentro de la víctima.** Ejecutar la preparación en una ventana autorizada y sin corridas activas. No borres la BD de Guacamole ni ejecutes `docker compose down -v`.

## A. Identifica qué reto estás intentando iniciar

| Código de reto | Mecanismo de evidencia | Requisito para habilitar |
| --- | --- | --- |
| `LAB-01` | Archivo dinámico `/opt/ctf/flag.txt` en LAB-LNXVICT | Inyector root-owned instalado, cuenta SSH con `sudo -n` restringido, VM y Guacamole listos |
| `ESC-01-RECON` | Archivo privado dinámico leído por HTTP `10.10.30.12:18081/evidence` | Inyector + servicio `ctf-evidence.service` + grupo `ctf-evidence` + Kali con permisos Guacamole |
| `ESC-02-BRUTEFORCE` | **Servicio SSH didáctico** en `10.10.30.12:2222`; flag temporal por corrida | Cuenta SSH/SFTP de backend + `python3` y módulo `paramiko` en LAB-LNXVICT + Kali con acceso |
| `ESC-06-WEBAUTH` / `ESC-07-EXPOSED` | Servicio HTTP didáctico en víctima `10.10.30.12:18082` | Cuenta SSH/SFTP backend + Python y permisos Guacamole en Kali |
| `ESC-03-WEBEXPLOIT` | Flag dinámica SQL dentro de MariaDB en `LAB-SRVWEB 10.10.30.20` | Sistema separado `labops`, clave SSH, `known_hosts` y `DVWA_LAB_ENABLED=true`; **deshabilitado por defecto** |
| `WEB-CONDOR` | Flag estática del portal compartido | **No necesita inyector SSH dinámico**; el instructor debe registrar la flag de la instalación |

**Importante:** el servicio de práctica SSH estaba usando `192.168.146.137/134` de VMware. Ya se corrigió a **víctima `10.10.30.12` y atacantes `10.10.20.10/.11/.12`**. También se actualizó el servicio HTTP y de evidencia, pero hay que actualizar sus archivos en la VM cuando corresponda.

## B. Paso 1: actualizar API y frontend sin borrar información

Desde la VM de aplicación **10.10.10.13**, en el directorio real del proyecto:

```bash
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin main
sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml build api web
sudo docker compose -f docker-compose.prod.yml up -d --no-deps api web
sudo docker compose -f docker-compose.prod.yml ps
```

Si el temporizador automático está instalado y activo, normalmente actualizará el commit aprobado sin estos comandos. **No ejecutes otro despliegue simultáneo.** Asegúrate de estar en `main` y no tener modificaciones locales: no usar `reset --hard` para forzar este proceso.

## C. Paso 2: diagnóstico de SOLO LECTURA desde la API

```bash
sudo docker compose -f docker-compose.prod.yml exec -T api python -m app.check_flag_injector
```

Este comando no crea ni revela ninguna bandera. Revisa los resultados:

| Comprobación | Interpretación si es `false` |
| --- | --- |
| `inyector_activado` | `FLAG_INJECTOR_ENABLED` no está activo en `.env` privado del contenedor |
| `tcp_ssh_desde_api` | No hay ruta o SSH operativo entre contenedor API → `10.10.30.12:22` |
| `autenticacion_ssh` | Usuario, contraseña/clave SSH o host key incorrectos |
| `ssh_sftp` | El usuario no puede escribir el servicio de práctica en su directorio personal |
| `inyector_instalado` | Falta `/usr/local/sbin/ctf-inject-flag.sh` en la VM |
| `sudo_sin_password` | El usuario no tiene la regla sudo restringida para ejecutar el inyector |
| `paramiko_en_victima` | No se podrá iniciar `ESC-02-BRUTEFORCE` en el puerto didáctico |

**No compartas el `.env`, contraseñas, claves privadas, tokens ni el contenido de flags.** Puedes compartir solo el JSON de este diagnóstico después de revisar que no contiene datos sensibles.

## D. Paso 3: preparar una sola vez LAB-LNXVICT (10.10.30.12)

Primero entra con la cuenta SSH autorizada para mantenimiento. Desde una terminal **en LAB-LNXVICT**, comprueba:

```bash
ip -br a
sudo systemctl status ssh --no-pager
python3 --version
python3 -c 'import paramiko; print("Paramiko disponible")'
sudo test -f /usr/local/sbin/ctf-inject-flag.sh && echo "Inyector instalado"
```

Si falta `paramiko` en la VM y el administrador lo permite, instala el paquete de Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3-paramiko
```

Instalar el inyector root-owned para la **cuenta SSH de servicio que YA esté configurada en el .env**:

1. Desde el servidor web, copia **solo** el instalador y el inyector a una carpeta temporal de la cuenta SSH autorizada de la víctima:

```bash
ssh ctf-lab-lnxvict@10.10.30.12 'mkdir -p ~/ctf-lab-setup'
scp backend/app/infrastructure/injection/scripts/linux/ctf-inject-flag.sh \
    backend/app/infrastructure/injection/scripts/linux/install-ctf-flag-injector.sh \
    ctf-lab-lnxvict@10.10.30.12:~/ctf-lab-setup/
```

2. En la víctima (no en el contenedor), como administrador:

```bash
sudo bash ~/ctf-lab-setup/install-ctf-flag-injector.sh ctf-lab-lnxvict
sudo visudo -cf /etc/sudoers.d/ctf-flag-injector-ctf-lab-lnxvict
sudo test -f /usr/local/sbin/ctf-inject-flag.sh && echo "Inyector presente"
sudo -n -l /usr/local/sbin/ctf-inject-flag.sh
```

La última orden, ejecutada desde la **cuenta SSH de servicio**, debe comprobar que el permiso `NOPASSWD` existe; **no** genera ninguna bandera. Si la cuenta no tiene permiso sudo para el instalador, debe hacerlo otro administrador desde la consola de VM. El instalador no altera contraseñas ni reemplaza automáticamente una versión diferente del script ya instalada; en ese caso planifica una revisión de mantenimiento.

Después vuelve a ejecutar **Paso C** desde la API. El servicio de práctica SSH se transfiere mediante SFTP al iniciar el reto (no se instala permanentemente a mano) y solo escuchará en `2222` cuando esté preparado, por lo que el puerto **puede aparecer cerrado antes de iniciar un reto**.

## E. Paso 4: comprobar inventario y permisos Guacamole

En **Administración > Laboratorios**:

- `LAB-LNXVICT` está registrada una sola vez en `10.10.30.12`, SO Linux/Ubuntu; el laboratorio y la VM están en estado **ready** (solo después de comprobar la conectividad real).
- `LAB-KALI` está registrada una sola vez en `10.10.20.10`, laboratorio y VM `ready`.
- No hay duplicados de IP o de nombre para estas dos máquinas.

En **Administración > Guacamole**:

- La API devuelve conexiones reales del servidor independiente (no `stub`).
- La cuenta estudiante tiene **READ** sobre la conexión SSH/RDP de Kali. Algunos retos necesitan una conexión SSH del destino Linux registrada, pero no deben dar al estudiante acceso directo privilegiado a la víctima.
- Si aparece «Inventario no verificado», revisa la CA/certificado del proxy HTTPS, acceso Guacamole y credenciales de servicio. **No crees conexiones duplicadas**.

En **Administración > Retos**:

- El reto está **publicado** y asignado al grupo activo del estudiante.
- Para retos dinámicos, conserva **una bandera dinámica activa** con plantilla válida.
- Para ESC-02: código `ESC-02-BRUTEFORCE`, escenario `SSH-PASSWORD-LAB`, activos `LAB-KALI` y `LAB-LNXVICT`.
- Para ESC-01: código `ESC-01-RECON`, escenario `ESC-01-RECON`, activos víctima `LAB-LNXVICT` y atacante `LAB-KALI`.
- Para DVWA: sigue `Docs/NUTANIX_DVWA_LAB_SRVWEB_IMPLEMENTACION.md`; no se soluciona instalando el inyector en LNXVICT.

## F. Paso 5: prueba del estudiante y diagnóstico por tipo de error

En una cuenta de estudiante perteneciente al grupo, abre **Retos** → elige `ESC-02-BRUTEFORCE` → **Iniciar reto**. La API debe preparar el usuario temporal, puerto `2222` y flag de la corrida. Desde Kali se realiza la práctica solo contra `10.10.30.12:2222` y se envía la bandera; al cerrar, se elimina el registro temporal.

| HTTP / mensaje | Qué corregir |
| --- | --- |
| 403 «no asignado a tu grupo» | Vincular grupo activo y reto al estudiante |
| 409 «Kali no está lista» | Inventario único/ready y permisos READ en Guacamole |
| 409 «requiere una flag dinámica activa» | Revisar tipo, plantilla y flag activa |
| 409 «escenario/VM no coincide» | Corregir código, escenario y activos |
| 503 «no pudo preparar SSH de práctica» | Diagnóstico de SSH/SFTP/Paramiko en LNXVICT; confirmar código nuevo desplegado |
| 503 «no pudo escribir la flag en la VM» | Inyector, `sudo -n` y scripts instalados, y ruta `/opt/ctf` |
| 503 por reserva de Redis | Verificar contenedor ↔ Redis `10.10.10.14`, no borrar locks manualmente con estudiantes activos |
| Error de certificado HTTPS | Corregir el proxy TLS de CoCiber (ver `Docs/RECUPERACION_TLS_GUACAMOLE_PRODUCCION.md`) |

Para ver solo logs de la aplicación, sin imprimir credenciales:

```bash
sudo docker compose -f docker-compose.prod.yml logs --tail=100 api
```

**No restaures snapshots de Nutanix mientras haya estudiantes conectados. No uses credenciales administrativas contra el puerto 2222**: ese servicio es exclusivamente de práctica y no autentica cuentas del sistema.

## G. Requisitos de seguridad

El `.env` compartido anteriormente contiene credenciales expuestas y `FLAG_INJECTOR_STRICT_HOST_KEY=false`. Tras estabilizar el laboratorio, rota las claves expuestas y utiliza una cuenta técnica dedicada y un `known_hosts` verificado. **No copies contraseñas a Git**, ni publiques el archivo `.env` con ellas. Mantén la VM LAB-LNXVICT accesible solo a través de las VLAN y permisos necesarios.

**Nota:** instalar el inyector y corregir las IPs habilita los prerrequisitos de los retos Linux. Las flags DVWA usan otro mecanismo; Operación Cóndor conserva una flag estática. El éxito final requiere prueba en vivo con cuentas de estudiante.
