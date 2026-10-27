# DVWA en LAB-SRVWEB: implementación para administradores (principiantes)

**Infraestructura:** Nutanix AHV · Víctima `LAB-SRVWEB 10.10.30.20` (VLAN30), atacante `LAB-KALI 10.10.20.10` (VLAN20). **Solo se autoriza el laboratorio.** No dirigir tráfico a Internet ni permitir DNAT de esta VM. No confundir este reto con la aplicación Cóndor del puerto 8080.

## A. Comprobar la instalación ya existente (no reinstalar sin necesidad)

El documento `33_Fase5_App_Vulnerable_LAB_SRVWEB.md` especifica DVWA en `http://10.10.30.20/dvwa/`, Apache/PHP y MariaDB. Comprueba desde la consola de LAB-SRVWEB:

```bash
ip -4 address
sudo systemctl is-active apache2 mariadb
sudo ss -ltnp | grep -E '(:80|:3306)'
sudo mariadb -N -e "SHOW TABLES FROM ctf_app_db;"
sudo mariadb -N -e "SELECT id FROM ctf_app_db.secrets ORDER BY id LIMIT 10;"
```

La base `dvwa` es diferente de `ctf_app_db`. `ctf_app_db.secrets` conserva la fila 1 de diagnóstico. **No muestres los valores `flag` en público.** Confirma que MariaDB escucha solo en `127.0.0.1:3306`.

Si DVWA no está instalado, sigue primero el documento de instalación original. No ejecutes `setup.php` > Reset Database sin respaldar los datos.

## B. Preparar el inyector mínimo (operador de infraestructura)

1. Haz backup de MariaDB y verifica una restauración. Asegura que existe el snapshot base de AHV y que ninguna sesión trabaja en esa VM.
2. Crea o confirma la cuenta `labops` dedicada, con autenticación **solo mediante clave SSH** y acceso restringido desde la API `10.10.10.13`. Guarda la clave en un secreto privado montado en el contenedor API; **nunca en Git**.
3. Copia `backend/app/infrastructure/injection/scripts/linux/ctf-dvwa-flag.py` del repositorio, usando SSH administrativo autorizado, a `/usr/local/sbin/ctf-dvwa-flag`. El ejecutable necesita Python3 y `/usr/bin/mariadb`.
4. Ajusta permisos:

```bash
sudo chown root:root /usr/local/sbin/ctf-dvwa-flag
sudo chmod 0750 /usr/local/sbin/ctf-dvwa-flag
sudo visudo -f /etc/sudoers.d/ctf-dvwa-flag
```

Escribe en el editor **solo esta regla**, tras verificar la ruta exacta de `python3` en el encabezado del archivo:

```text
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-dvwa-flag --upsert *, /usr/local/sbin/ctf-dvwa-flag --delete *
```

**Nota de seguridad:** en sudoers los comodines admiten argumentos adicionales. Aunque el script limita estrictamente el ID, solicita a infraestructura sustituir la regla por una política de argumentos anclada en versiones de sudo compatibles o un servicio remoto con identidad fija. No concedas `sudo ALL`.

5. Prueba con una flag temporal de formato correcto (evita exponerla en historial de shell) y comprueba únicamente que aparece la fila temporal; luego elimina esa fila. El código rechaza modificar `id=1` y las filas de otros servicios. **Jamás permitas ejecutar el helper como servidor web público.**

## C. Configurar el backend

Conserva `.env` privado de producción. Añade:

```dotenv
DVWA_LAB_ENABLED=false
DVWA_LAB_SSH_USER=labops
DVWA_LAB_SSH_PRIVATE_KEY=/run/secrets/dvwa_lab_ssh_key
DVWA_LAB_KNOWN_HOSTS=/run/secrets/dvwa_lab_known_hosts
```

La clave y `known_hosts` tienen que **existir dentro del contenedor API**: configura volúmenes de solo lectura aprobados por el administrador, sin exponerlos al frontend. En modo inicial `false` nadie puede iniciar el ejercicio. Una vez comprobada la conexión y la inyección/limpieza en un entorno piloto, cambia a `true` y recrea únicamente la API.

## D. Registrar un reto, sin publicarlo automáticamente

Tras confirmar el nombre exacto del grupo, desde el directorio de despliegue:

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps api python configure_dvwa_catalog.py --group CODIGO_DEL_GRUPO
```

El primer comando **simula y revierte** los cambios. Revisa su resultado y solo entonces aplica:

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps api python configure_dvwa_catalog.py --group CODIGO_DEL_GRUPO --apply
```

Si el código `ESC-03-WEBEXPLOIT` ya está registrado con configuración distinta, el proceso se detiene y **no lo sobrescribe**. Comprueba manualmente el estado de publicación. Nunca habilites en producción sin una corrida piloto exitosa.

## E. Preparar el snapshot AHV

El snapshot se restaura **solo con la VM libre y previa autorización**. Restaurar durante una corrida invalida la bandera de otros estudiantes. Hasta disponer de clonación por grupo, planifica turnos de uso o controla estado de sesiones activas. El cierre del reto limpia su fila SQL, **no** invoca automáticamente la API de Prism Central/AHV.

## F. Resultado correcto

Cada estudiante ve el `run_id` y el `row_id = 1000000 + run_id` de su corrida. El backend calcula `FLAG{dvwa_sql_<40 caracteres hex>}`, almacena solo el hash en PostgreSQL y escribe el valor temporal dentro de `ctf_app_db.secrets`. El alumno debe recuperar su fila por SQL Injection y enviarla a Cociber. Al cerrar se elimina **solo esa fila** y no se reinicia DVWA. `Reset Database` tampoco elimina `ctf_app_db.secrets`.

**Estado:** código preparado para piloto; no se verificó desde el servidor AHV y no garantiza todavía 6 sesiones simultáneas.
