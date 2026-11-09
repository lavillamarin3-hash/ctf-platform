# Helpers nuevos para ESC-02, ESC-03 y sesiones Kali

Esta guía es para la **instalación nueva**. No se ha ejecutado automáticamente en las VM. Primero termina y limpia las corridas de la plataforma histórica que usen esas víctimas, guarda un snapshot y reserva una ventana de mantenimiento. Mantén una sesión administrativa abierta al validar SSH.

El archivo `labs/fresh/helpers/ctf-lab-helper.py` contiene tres comportamientos según el nombre con el que se instala. No reemplaza `ctf-ssh-practice.py` ni `ctf-dvwa-flag` del despliegue anterior.

## 1. Transferir el archivo

Desde un equipo con el clon, copia el helper mediante el salto real de administración. Por ejemplo, desde Linux/WSL o una terminal que disponga de scp:

```bash
scp -o ProxyJump=lab-rtrfw@10.195.20.20 labs/fresh/helpers/ctf-lab-helper.py lab-lnxvict@10.10.30.12:/tmp/ctf-lab-helper.py
scp -o ProxyJump=lab-rtrfw@10.195.20.20 labs/fresh/helpers/ctf-lab-helper.py lab-srvweb@10.10.30.20:/tmp/ctf-lab-helper.py
```

Para cada Kali usa su cuenta de administración existente y la IP del inventario (.10, .11 o .12 de VLAN20). Esa cuenta no está confirmada en el contexto: no se inventa un username en esta guía. La contraseña se introduce de forma interactiva.

## 2. Cuenta técnica y claves

En cada VM, verifica si `labops` ya existe con `id labops`. Si existe, conserva sus claves autorizadas y configuración. Si no existe, crea una cuenta de servicio y configura su acceso SSH con la **clave pública** preparada en LAB-CTFWEB. No copies claves privadas a las víctimas.

El home de labops y `.ssh/authorized_keys` deben pertenecer a labops, con `.ssh` 0700 y `authorized_keys` 0600. Antes de activar la integración, verifica la huella de host desde la consola administrativa y añádela al `known_hosts` privado montado por la API. No uses `StrictHostKeyChecking=no` ni aceptes a ciegas la salida de ssh-keyscan.

La nueva API usa una clave `labops_ed25519` y `known_hosts` según `deploy/fresh.env.example`. Los hosts permitidos por el adaptador son exactamente las tres Kali, LAB-LNXVICT y LAB-SRVWEB; no acepta hosts suministrados por jugadores.

## 3. LAB-LNXVICT: SSH didáctico en 2222

En LAB-LNXVICT:

```bash
sudo groupadd -f cociber-ssh
sudo install -o root -g root -m 0755 /tmp/ctf-lab-helper.py /usr/local/sbin/ctf-ssh-lab
sudo python3 -m py_compile /usr/local/sbin/ctf-ssh-lab
sudo ss -lntp
```

Si 2222 ya está ocupado por el servicio anterior, **no arranques otra instancia**: identifica su unidad/proceso y planifica su sustitución después del drenaje. No mates procesos por número de puerto sin identificar su propietario.

Copia `labs/fresh/helpers/sshd-practice.conf` y `cociber-sshd.service` a `/tmp` de esa VM y después:

```bash
sudo install -o root -g root -m 0644 /tmp/sshd-practice.conf /etc/ssh/sshd-practice.conf
sudo install -o root -g root -m 0644 /tmp/cociber-sshd.service /etc/systemd/system/cociber-sshd.service
sudo /usr/sbin/sshd -t -f /etc/ssh/sshd-practice.conf
```

Antes de iniciar, restringe en el **sshd administrativo** el acceso del grupo `cociber-ssh`, conservando las reglas existentes. La directiva a incorporar es `DenyGroups cociber-ssh`; si ya hay DenyGroups, añade el grupo a la misma política sin eliminar los otros. Revisa cómo carga el servidor sus archivos Include, valida `sudo sshd -t`, recarga la unidad SSH real y prueba una segunda conexión de mantenimiento **antes de cerrar la primera**. Esta restricción no va en el archivo didáctico, que utiliza `AllowGroups cociber-ssh`.

Después de validar la administración y que 2222 está libre:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cociber-sshd.service
sudo systemctl status cociber-sshd.service --no-pager
```

El usuario de práctica será `ctf_<run_id>` con una clave elegida entre doce candidatas y un archivo `~/flag.txt` 0400. La API nunca entrega la contraseña elegida. El servidor didáctico bloquea root, forwarding, túneles y agentes. El cierre de la corrida elimina la cuenta y sus procesos; supervisar el worker es necesario para que el cierre ocurra.

## 4. Kali: usuario efímero por corrida

En **cada Kali que vaya a marcarse disponible**, instala:

```bash
sudo groupadd -f cociber-kali
sudo install -o root -g root -m 0755 /tmp/ctf-lab-helper.py /usr/local/sbin/ctf-kali-session
sudo python3 -m py_compile /usr/local/sbin/ctf-kali-session
sudo /usr/sbin/sshd -T
```

Confirma que el SSH de Kali permite autenticación por contraseña para los usuarios de práctica y que una política AllowUsers/AllowGroups no los excluye. No elimines restricciones administrativas existentes; añade una regla acotada para el grupo de práctica si es necesaria y valida el resultado antes de recargar.

El helper crea `ctf_<run_id>` sin sudo, con contraseña aleatoria fuerte recibida por stdin. Guacamole recibe esa cuenta para una conexión SSH efímera. La clave débil de ESC-02 existe **solo en la víctima**, nunca en la Kali.

El helper Kali acepta create/destroy; incluye check para comprobación administrativa, aunque el contrato de orquestación solo utiliza las dos primeras acciones.

## 5. LAB-SRVWEB: evidencia DVWA

En LAB-SRVWEB:

```bash
sudo install -o root -g root -m 0755 /tmp/ctf-lab-helper.py /usr/local/sbin/ctf-dvwa-lab
sudo python3 -m py_compile /usr/local/sbin/ctf-dvwa-lab
sudo mariadb -e 'SHOW CREATE TABLE ctf_app_db.secrets\G'
```

El contrato nuevo requiere `run_id CHAR(12)` y `flag VARCHAR(128)`. El helper antiguo utilizaba un ID numérico: **no son esquemas intercambiables**. Si la tabla existe con el esquema anterior, detén aquí la preparación del nuevo helper y respalda/planifica el cambio con el responsable de BD o utiliza una copia aislada de la víctima. No se ofrece un DROP ni un ALTER que pueda romper las corridas antiguas.

Solo si es una tabla nueva dentro de una víctima preparada para esta instalación:

```sql
CREATE DATABASE IF NOT EXISTS ctf_app_db;
CREATE TABLE ctf_app_db.secrets (
    run_id CHAR(12) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    flag VARCHAR(128) NOT NULL
);
```

No uses `CREATE TABLE IF NOT EXISTS` para ocultar un esquema incompatible. La cuenta local root de MariaDB debe funcionar por socket con `sudo mariadb` y sin poner su contraseña en argumentos. Identifica la cuenta de conexión de **DVWA** en su configuración local y concede a esa cuenta, desde su origen real, únicamente `SELECT` sobre `ctf_app_db.secrets`. No se inventa un nombre de usuario ni se concede acceso global. El helper escribe como root local; el jugador investiga usando los permisos limitados de DVWA.

Confirma `http://10.10.30.20/dvwa/`, la cuenta de práctica de DVWA y nivel Low desde Kali. La cuenta y contraseña DVWA no vienen definidas por este refactor. Al cerrar, destroy elimina solamente la fila de ese run_id; no lee stdin y no queda esperando entrada.

## 6. Sudo restringido, una regla por VM

Abre `sudo visudo -f /etc/sudoers.d/cociber-fresh` y escribe **solo la línea correspondiente a esa VM**:

```sudoers
# LAB-LNXVICT
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-ssh-lab create *, /usr/local/sbin/ctf-ssh-lab check *, /usr/local/sbin/ctf-ssh-lab destroy *
```

```sudoers
# LAB-SRVWEB
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-dvwa-lab create *, /usr/local/sbin/ctf-dvwa-lab check *, /usr/local/sbin/ctf-dvwa-lab destroy *
```

```sudoers
# Cada Kali
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-kali-session create *, /usr/local/sbin/ctf-kali-session destroy *
```

Los comodines de sudoers no validan el run_id; esa comprobación la realiza el helper root-owned, que exige exactamente dos argumentos y 12 hex. No concedas `python3 *`, shell general ni escritura del script a labops. El directorio `/usr/local/sbin` también debe impedir escritura de labops y estudiantes.

```bash
sudo chmod 0440 /etc/sudoers.d/cociber-fresh
sudo visudo -cf /etc/sudoers.d/cociber-fresh
sudo -u labops sudo -n -l
```

## 7. Prueba desde la plataforma y habilitación

Usa los comandos de prueba de [INSTALACION_NUEVA_COCIBER.md](INSTALACION_NUEVA_COCIBER.md). El helper devuelve JSON sin flags/contraseñas; check devuelve `flag_hash`. La plataforma compara ese hash con el de la bandera generada para la prueba. Para marcar un piloto aprobado también deben completarse la cuenta Kali, la conexión Guacamole y la limpieza.

Si una prueba falla, la VM continúa drenada. Revisa su servicio, permisos y esquema. No cambies estado manualmente a ready para evitar un error de inyección y no actives variables ENABLED antes de tener resultados correctos.

Después del piloto, realiza una corrida humana con un usuario de prueba: confirma que abre la consola, llega al servicio didáctico y que al cerrar desaparecen usuario, conexión y evidencia de esa corrida. Esta comprobación real no se ha ejecutado desde el entorno de desarrollo.
