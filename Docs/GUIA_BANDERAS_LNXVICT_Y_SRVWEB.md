# Banderas dinámicas: LNXVICT y SRVWEB

Esta guía habilita exclusivamente los dos laboratorios de demostración:

| Reto | Atacante | Víctima | Mecanismo de bandera |
| --- | --- | --- | --- |
| `ESC-02-BRUTEFORCE` | `LAB-KALI-BLUE` (`10.10.20.12`) | `LAB-LNXVICT` (`10.10.30.12`) | Servicio SSH didáctico temporal en `2222` |
| `ESC-03-WEBEXPLOIT` | `LAB-KALI-PURPLE` (`10.10.20.11`) | `LAB-SRVWEB` (`10.10.30.20`) | Fila temporal en `ctf_app_db.secrets` mediante DVWA |

No pongas las contraseñas de mantenimiento, claves privadas ni flags dentro de
`.env`, Git, Markdown, capturas o comandos con historial. Las credenciales
administrativas de las VMs se usan solo para entrar de forma interactiva y
crear cuentas técnicas con clave SSH.

## 0. Preparación común

1. Reserve una ventana sin estudiantes ni corridas activas.
2. Confirme snapshots de `LAB-LNXVICT` y `LAB-SRVWEB`; no los restaure durante
   una corrida.
3. Desde el equipo de operación, conecte a cada VM a través del router:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
```

Introduzca las contraseñas solo cuando SSH las solicite. Si el salto requiere
una clave propia, use su clave autorizada; no intente almacenarla en la
plataforma ni copiarla a este repositorio.

4. En `LAB-CTFWEB` (`10.10.10.13`), entre al checkout de producción, confirme
   que incorpora esta versión y cree un directorio privado para los secretos
   de servicio:

```bash
git pull --ff-only origin main
sudo install -d -o root -g root -m 0750 /opt/cociber-secrets
sudo ssh-keygen -t ed25519 -f /opt/cociber-secrets/lnxvict_ctf_ed25519 -N '' -C 'cociber-api-lnxvict'
sudo ssh-keygen -t ed25519 -f /opt/cociber-secrets/srvweb_labops_ed25519 -N '' -C 'cociber-api-srvweb'
```

Conserve los archivos `.pub` para copiarlos a las VMs. Las claves privadas no
salen de CTFWEB. Antes de crear cada `known_hosts`, compare la huella SSH de
la consola de la VM con la obtenida desde CTFWEB; solo entonces ejecute:

```bash
sudo ssh-keyscan -H 10.10.30.12 | sudo tee /opt/cociber-secrets/lnxvict_known_hosts >/dev/null
sudo ssh-keyscan -H 10.10.30.20 | sudo tee /opt/cociber-secrets/srvweb_known_hosts >/dev/null
sudo chown root:10001 /opt/cociber-secrets/*
sudo chmod 0640 /opt/cociber-secrets/*_ed25519
sudo chmod 0644 /opt/cociber-secrets/*_known_hosts
```

El GID `10001` corresponde al usuario `appuser` del contenedor API. En el
host puede mostrarse como `UNKNOWN` si no existe un grupo local con ese nombre;
lo importante es que el GID numérico sea `10001`. Compruébelo sin mostrar las
claves con `sudo stat -c '%u:%g %a %n' /opt/cociber-secrets/*_ed25519`.

## 1. LAB-LNXVICT: servicio para ESC-02

### 1.1 Crear la cuenta técnica

Entre a LNXVICT con la cuenta de mantenimiento y confirme primero:

```bash
hostname
ip -br -4 address
sudo systemctl is-active ssh
python3 --version
python3 -c 'import paramiko; print("paramiko disponible")'
```

Si `paramiko` no está instalado, el administrador debe instalar el paquete de
la distribución desde el repositorio autorizado o un paquete interno:

```bash
sudo apt-get update
sudo apt-get install -y python3-paramiko
```

Cree la cuenta que la API utilizará solo para SFTP y el proceso didáctico. No
requiere `sudo` ni contraseña interactiva:

```bash
id ctf-injector >/dev/null 2>&1 || sudo useradd --create-home --shell /bin/bash ctf-injector
sudo install -d -o ctf-injector -g ctf-injector -m 0700 /home/ctf-injector/.ssh
sudo install -o ctf-injector -g ctf-injector -m 0600 /dev/null /home/ctf-injector/.ssh/authorized_keys
```

Desde CTFWEB copie **solamente** la clave pública a un temporal de LNXVICT:

```bash
sudo scp /opt/cociber-secrets/lnxvict_ctf_ed25519.pub \
  lab-lnxvict@10.10.30.12:/tmp/lnxvict_ctf_ed25519.pub
```

En LNXVICT instálela para la cuenta técnica y valide:

```bash
sudo install -o ctf-injector -g ctf-injector -m 0600 \
  /tmp/lnxvict_ctf_ed25519.pub /home/ctf-injector/.ssh/authorized_keys
sudo chown -R ctf-injector:ctf-injector /home/ctf-injector/.ssh
sudo chmod 0700 /home/ctf-injector/.ssh
sudo chmod 0600 /home/ctf-injector/.ssh/authorized_keys
```

No instale `/usr/local/sbin/ctf-inject-flag.sh` para este reto: corresponde a
`LAB-01`; `ESC-02` crea y borra registros privados en
`~ctf-injector/.ctf-ssh-practice/` mediante SFTP.

### 1.2 Verificar la clave desde CTFWEB

La clave original debe conservarse como `root:10001` con modo `0640`: el
grupo `10001` permite que el contenedor API la lea. OpenSSH ejecutado en el
host la rechaza correctamente por ser legible por un grupo. No cambie la
clave original a `0600`, porque la API dejaría de poder leerla.

Para probarla desde el host, cree una copia temporal exclusiva de `root` y
elimínela automáticamente al terminar:

```bash
(
  set -e
  sudo install -o root -g root -m 0600 \
    /opt/cociber-secrets/lnxvict_ctf_ed25519 /run/cociber-lnxvict-verify.key
  trap 'sudo rm -f /run/cociber-lnxvict-verify.key' EXIT
  sudo ssh -i /run/cociber-lnxvict-verify.key \
    -o UserKnownHostsFile=/opt/cociber-secrets/lnxvict_known_hosts \
    -o StrictHostKeyChecking=yes ctf-injector@10.10.30.12 \
    'python3 -c "import paramiko; print(\"OK\")"'
)
```

El resultado debe ser únicamente `OK`. Si falla, corrija la clave pública,
propiedad de `authorized_keys`, la huella de host o el enrutamiento VLAN 10 →
VLAN 30; no active la variable de entorno todavía.

### 1.3 Completar `.env` privado en CTFWEB

Edite el `.env` de producción existente. Cambie **solo** estas líneas:

```dotenv
FLAG_INJECTOR_ENABLED=true
FLAG_INJECTOR_SSH_USER=ctf-injector
FLAG_INJECTOR_SSH_PASSWORD=
FLAG_INJECTOR_SSH_PRIVATE_KEY=/run/secrets/lnxvict_lab_ssh_key
FLAG_INJECTOR_KNOWN_HOSTS=/run/secrets/lnxvict_lab_known_hosts
FLAG_INJECTOR_SSH_PORT=22
FLAG_INJECTOR_STRICT_HOST_KEY=true
FLAG_INJECTOR_SSH_PRIVATE_KEY_HOST=/opt/cociber-secrets/lnxvict_ctf_ed25519
FLAG_INJECTOR_KNOWN_HOSTS_HOST=/opt/cociber-secrets/lnxvict_known_hosts
```

No cambie `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, Guacamole ni las demás
variables. Las rutas terminadas en `_HOST` pertenecen al host CTFWEB; las
rutas `/run/secrets/...` existen dentro del contenedor.

### 1.4 Desplegar y registrar el reto SSH

Desde el checkout de CTFWEB, sustituya `GRUPO_PILOTO` por un grupo activo:

```bash
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml config --quiet
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml up -d --force-recreate api
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml exec -T api \
  python -m app.check_flag_injector
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml exec -T api \
  python configure_ssh_access_challenge.py --group GRUPO_PILOTO --attacker LAB-KALI-BLUE
```

En el JSON de diagnóstico, `ready_for_ssh_practice` debe ser `true`. Para
`ESC-02`, que `inyector_instalado` y `sudo_sin_password` sean `false` es
normal: esos requisitos pertenecen a LAB-01/ESC-01 y no al servicio SSH
didáctico.

Revise el JSON del último comando. Si el plan es correcto, aplíquelo:

```bash
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml exec -T api \
  python configure_ssh_access_challenge.py --group GRUPO_PILOTO --attacker LAB-KALI-BLUE --apply
```

El configurador deja un reto nuevo en borrador. Publíquelo desde la interfaz
solo tras validar la conexión Guacamole SSH/RDP de `LAB-KALI-BLUE` y asignar
el grupo piloto. La primera corrida transfiere automáticamente el servicio
SSH didáctico; antes de iniciarla no es obligatorio que el puerto 2222 esté
escuchando.

## 2. LAB-SRVWEB: DVWA y ESC-03

### 2.1 Confirmar DVWA y MariaDB

Entre a SRVWEB y ejecute solo comprobaciones que no muestren flags:

```bash
hostname
ip -br -4 address
sudo systemctl is-active apache2 mariadb
sudo ss -ltnp | grep -E '(:80|:3306)'
sudo mariadb -N -e 'SHOW DATABASES LIKE "dvwa";'
```

Apache debe servir DVWA en `http://10.10.30.20/dvwa/` y MariaDB debe escuchar
localmente. No exponga el puerto 3306 a VLAN 20 ni a la red de gestión.

### 2.2 Crear base de evidencias y permiso SQL mínimo

La base `ctf_app_db` es independiente de la base `dvwa`. Cree la tabla y una
fila de diagnóstico sin valor de flag:

```bash
sudo mariadb <<'SQL'
CREATE DATABASE IF NOT EXISTS ctf_app_db;
CREATE TABLE IF NOT EXISTS ctf_app_db.secrets (
  id INT NOT NULL PRIMARY KEY,
  flag VARCHAR(80) NOT NULL
);
INSERT IGNORE INTO ctf_app_db.secrets (id, flag) VALUES (1, 'diagnostic-row');
SQL
```

Identifique de forma privada el usuario MariaDB configurado en DVWA. En una
instalación estándar suele ser `dvwa`; no copies su contraseña ni su archivo
de configuración al chat. Para confirmar solo usuario y host, sin revelar
contraseñas:

```bash
sudo mariadb -N -e "SELECT User,Host FROM mysql.user WHERE User='dvwa';"
```

Otórgale solamente lectura sobre la tabla, respetando el host mostrado:

```bash
sudo mariadb
```

Dentro de MariaDB, sustituyendo el usuario si fuera distinto:

```sql
GRANT SELECT ON ctf_app_db.secrets TO 'dvwa'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2.3 Instalar `labops` y el helper restringido

Copie la clave pública y el helper desde CTFWEB a temporales de SRVWEB:

```bash
sudo scp /opt/cociber-secrets/srvweb_labops_ed25519.pub \
  lab-srvweb@10.10.30.20:/tmp/srvweb_labops_ed25519.pub
sudo scp backend/app/infrastructure/injection/scripts/linux/ctf-dvwa-flag.py \
  lab-srvweb@10.10.30.20:/tmp/ctf-dvwa-flag.py
```

En SRVWEB cree la cuenta y restrinja el acceso por clave:

```bash
id labops >/dev/null 2>&1 || sudo useradd --create-home --shell /bin/bash labops
sudo install -d -o labops -g labops -m 0700 /home/labops/.ssh
sudo install -o labops -g labops -m 0600 /dev/null /home/labops/.ssh/authorized_keys
sudo install -o labops -g labops -m 0600 \
  /tmp/srvweb_labops_ed25519.pub /home/labops/.ssh/authorized_keys
sudo chown -R labops:labops /home/labops/.ssh
```

En SRVWEB instale el helper ya copiado. Si el helper se instaló antes de una
actualización del repositorio, repita esta copia e instalación: la versión
actual no lee `stdin` al ejecutar `--delete`.

```bash
sudo install -o root -g root -m 0750 /tmp/ctf-dvwa-flag.py /usr/local/sbin/ctf-dvwa-flag
sudo visudo -f /etc/sudoers.d/ctf-dvwa-flag
```

En el editor escriba exactamente una línea:

```text
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-dvwa-flag --upsert *, /usr/local/sbin/ctf-dvwa-flag --delete *
```

Guarde y valide antes de cerrar:

```bash
sudo visudo -cf /etc/sudoers.d/ctf-dvwa-flag
sudo -u labops sudo -n -l /usr/local/sbin/ctf-dvwa-flag
```

Prueba controlada, sin usar una flag de un estudiante. El ID máximo elegido
no puede corresponder a una corrida válida de la plataforma:

```bash
TEST_ROW_ID=2147483647
sudo -u labops python3 -c "print('FLAG{dvwa_sql_' + '0'*40 + '}')" | \
  sudo -u labops sudo -n /usr/local/sbin/ctf-dvwa-flag --upsert "$TEST_ROW_ID"
sudo -u labops sudo -n /usr/local/sbin/ctf-dvwa-flag --delete "$TEST_ROW_ID"
sudo mariadb -N -e "SELECT COUNT(*) FROM ctf_app_db.secrets WHERE id=$TEST_ROW_ID;"
```

El último comando debe devolver `0`. Si no lo hace, no habilite DVWA.

### 2.4 Completar `.env` privado y montar secretos DVWA

En el `.env` de CTFWEB agregue o ajuste:

```dotenv
DVWA_LAB_ENABLED=false
DVWA_LAB_SSH_USER=labops
DVWA_LAB_SSH_PRIVATE_KEY=/run/secrets/dvwa_lab_ssh_key
DVWA_LAB_KNOWN_HOSTS=/run/secrets/dvwa_lab_known_hosts
DVWA_LAB_SSH_PRIVATE_KEY_HOST=/opt/cociber-secrets/srvweb_labops_ed25519
DVWA_LAB_KNOWN_HOSTS_HOST=/opt/cociber-secrets/srvweb_known_hosts
```

Antes de activar el laboratorio, compruebe la autenticación desde CTFWEB.
La clave de SRVWEB también se comparte en modo `0640` con el contenedor y
por ello la validación con OpenSSH usa una copia temporal de `root`:

```bash
(
  set -e
  sudo install -o root -g root -m 0600 \
    /opt/cociber-secrets/srvweb_labops_ed25519 /run/cociber-srvweb-verify.key
  trap 'sudo rm -f /run/cociber-srvweb-verify.key' EXIT
  sudo ssh -i /run/cociber-srvweb-verify.key \
    -o UserKnownHostsFile=/opt/cociber-secrets/srvweb_known_hosts \
    -o StrictHostKeyChecking=yes labops@10.10.30.20 \
    'test -x /usr/local/sbin/ctf-dvwa-flag && sudo -n -l /usr/local/sbin/ctf-dvwa-flag >/dev/null && echo OK'
)
```

Si devuelve únicamente `OK`, cambie solo entonces a:

```dotenv
DVWA_LAB_ENABLED=true
```

Recree la API usando ambos overlays y registre el catálogo en modo ensayo:

```bash
sudo docker compose -f docker-compose.prod.yml \
  -f deploy/docker-compose.ssh-lab-secrets.yml \
  -f deploy/docker-compose.dvwa-lab-secrets.yml up -d --force-recreate api
sudo docker compose -f docker-compose.prod.yml \
  -f deploy/docker-compose.ssh-lab-secrets.yml \
  -f deploy/docker-compose.dvwa-lab-secrets.yml exec -T api \
  python configure_dvwa_catalog.py --group GRUPO_PILOTO
```

Revise que el resultado indique `LAB-KALI-PURPLE` y `LAB-SRVWEB`. Aplique solo
si el reto está inactivo y el grupo es correcto:

```bash
sudo docker compose -f docker-compose.prod.yml \
  -f deploy/docker-compose.ssh-lab-secrets.yml \
  -f deploy/docker-compose.dvwa-lab-secrets.yml exec -T api \
  python configure_dvwa_catalog.py --group GRUPO_PILOTO --apply
```

El configurador mantiene DVWA sin publicar. Publíquelo desde la interfaz para
el grupo piloto, abra una sola corrida desde Purple, valide la flag y cierre.
Tras el cierre, confirme sin revelar datos que no quedan filas de corrida:

```bash
sudo mariadb -N -e 'SELECT COUNT(*) FROM ctf_app_db.secrets WHERE id >= 1000001;'
```

Debe devolver `0` antes de dar acceso a otro estudiante.

## 3. Resultado y recuperación

Para cada reto, la aceptación mínima es: terminal Kali real, inicio de una
corrida, evidencia válida, puntos una sola vez, cierre y evidencia retirada.
No use `docker compose down -v`, `FLUSHDB`, restablecimiento de DVWA ni
snapshots durante una sesión activa. Si falla cualquier paso, deje el reto sin
publicar, vuelva `DVWA_LAB_ENABLED=false` para DVWA y conserve los registros
para diagnóstico.
