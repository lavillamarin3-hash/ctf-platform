# 11. LAB-SRVFSAD: FTP de práctica en Ubuntu Server 26.04

**Antes:** [09. Preparación](09_PREPARACION_WINDOWS_Y_FTP.md), snapshot previo y VM dedicada al laboratorio. Este procedimiento configura **vsftpd**, cuenta local de prueba, acceso pasivo y descarga de un archivo. No configura Samba ni habilita automáticamente ESC-05.

El FTP de esta demo transmite sin TLS y usa únicamente credenciales y archivos de prueba en VLAN20/30. No publiques el puerto 21 en la red de gestión/Internet ni reutilices credenciales administrativas. Si necesitas cifrado, prepara un ejercicio FTPS con certificado validado por separado; no confundas FTP, FTPS y SFTP.

## 1. Entrar y comprobar el estado previo

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-srvfsad@10.10.30.21
```

Dentro de **LAB-SRVFSAD**, Linux:

```bash
hostname
cat /etc/os-release
ip -brief address
sudo ss -lntp '( sport = :21 )'
dpkg-query -W vsftpd
sudo systemctl status vsftpd.service --no-pager
```

Esperado: Ubuntu 26.04 y `10.10.30.21`. Si vsftpd no está instalado, los dos últimos comandos pueden indicar paquete/unidad inexistentes. Si hay un FTP atendiendo usuarios, detente y conserva su configuración: los pasos siguientes están destinados a una instalación nueva. No sustituyas un servicio de archivos existente sin registrar sus datos y clientes.

Con acceso al repositorio Ubuntu autorizado:

```bash
sudo apt-get update
sudo apt-get install vsftpd
```

Después de instalar en esta VM nueva, detén la unidad predeterminada para preparar una configuración separada:

```bash
sudo systemctl disable --now vsftpd.service
sudo install -d -o root -g root -m 0755 /etc/cociber-ftp
```

No se toca `/etc/vsftpd.conf`. La instancia del laboratorio usará `/etc/cociber-ftp/vsftpd.conf` y `cociber-ftp.service`. Consulta la [referencia de vsftpd de Ubuntu 26.04](https://manpages.ubuntu.com/manpages/resolute/man5/vsftpd.conf.5.html) para los parámetros y el rango pasivo.

## 2. Crear una cuenta exclusiva de FTP

Comprueba primero:

```bash
id ctf_ftp_demo
sudo test -e /srv/cociber-ftp/ctf_ftp_demo && echo 'Ya existe la carpeta: revisar antes de continuar'
```

Si la cuenta o la carpeta existen, revisa su uso antes de continuar. **Solo con ambos nombres libres**:

```bash
sudo useradd --user-group --no-create-home --home-dir /srv/cociber-ftp/ctf_ftp_demo --shell /bin/bash ctf_ftp_demo
sudo passwd ctf_ftp_demo
sudo install -d -o root -g root -m 0755 /srv/cociber-ftp
sudo install -d -o root -g ctf_ftp_demo -m 0750 /srv/cociber-ftp/ctf_ftp_demo
printf 'EVIDENCIA_FTP: descarga de laboratorio correcta\n' | sudo tee /srv/cociber-ftp/ctf_ftp_demo/evidencia.txt > /dev/null
sudo chown root:ctf_ftp_demo /srv/cociber-ftp/ctf_ftp_demo/evidencia.txt
sudo chmod 0640 /srv/cociber-ftp/ctf_ftp_demo/evidencia.txt
```

`passwd` solicita dos veces una contraseña de práctica nueva sin mostrarla. La raíz del chroot pertenece a root; el usuario puede leer pero no modificar el archivo. La shell válida permite la validación PAM del paquete; el siguiente paso impide usar esta cuenta por SSH.

## 3. Denegar SSH a la cuenta de FTP

Mantén tu sesión administrativa abierta y respalda la configuración antes de editar:

```bash
sudo cp -a /etc/ssh/sshd_config "/etc/ssh/sshd_config.antes-ftp.$(date -u +%Y%m%dT%H%M%S).bak"
sudo nano /etc/ssh/sshd_config
```

En la sección global, antes de cualquier bloque `Match`, agrega `ctf_ftp_demo` a `DenyUsers`. Si no existe esa directiva, añade:

```text
DenyUsers ctf_ftp_demo
```

Conserva los usuarios ya denegados y revisa los archivos Include. Guarda con Ctrl+O, Enter y Ctrl+X. Valida:

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | grep '^denyusers '
sudo systemctl status ssh.service --no-pager
```

Solo si la sintaxis es correcta, aparece `ctf_ftp_demo` y la unidad SSH corresponde a esta instalación:

```bash
sudo systemctl reload ssh.service
```

Abre otra sesión administrativa desde PowerShell y confirma que `lab-srvfsad` sigue entrando antes de cerrar la original. No concedas sudo a `ctf_ftp_demo`.

## 4. Escribir la configuración de FTP

Antes de escribir, revisa si existen `/etc/cociber-ftp/vsftpd.conf`, `/etc/cociber-ftp/usuarios` o `/etc/systemd/system/cociber-ftp.service` con `sudo ls -l` seguido de esas rutas. Si ya existen por otra instalación, revísalos y respáldalos; no copies encima sin comprobar su origen. Para la configuración nueva:

```bash
printf 'ctf_ftp_demo\n' | sudo tee /etc/cociber-ftp/usuarios > /dev/null
sudo chmod 0644 /etc/cociber-ftp/usuarios
sudo tee /etc/cociber-ftp/vsftpd.conf > /dev/null <<'CONF'
listen=YES
listen_ipv6=NO
listen_address=10.10.30.21
listen_port=21
background=NO
anonymous_enable=NO
local_enable=YES
write_enable=NO
download_enable=YES
chroot_local_user=YES
allow_writeable_chroot=NO
local_root=/srv/cociber-ftp/$USER
user_sub_token=$USER
userlist_enable=YES
userlist_deny=NO
userlist_file=/etc/cociber-ftp/usuarios
pam_service_name=vsftpd
pasv_enable=YES
port_enable=NO
pasv_address=10.10.30.21
pasv_min_port=30000
pasv_max_port=30009
ssl_enable=NO
xferlog_enable=YES
xferlog_file=/var/log/cociber-ftp-transfers.log
ftpd_banner=CoCiber FTP de practica
idle_session_timeout=300
data_connection_timeout=60
max_clients=5
max_per_ip=2
secure_chroot_dir=/var/run/vsftpd/empty
CONF
sudo install -d -o root -g root -m 0755 /var/run/vsftpd/empty
```

Copia completo el bloque, incluido `CONF`. Las comillas de `<<'CONF'` mantienen `$USER` literal para vsftpd; no sustituyas ese valor por la cuenta administrativa de la sesión. Solo el usuario incluido en `usuarios` podrá autenticar por FTP.

## 5. Crear la unidad y arrancar

```bash
sudo tee /etc/systemd/system/cociber-ftp.service > /dev/null <<'UNIT'
[Unit]
Description=CoCiber FTP de practica
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
ExecStartPre=/usr/bin/install -d -o root -g root -m 0755 /var/run/vsftpd/empty
ExecStart=/usr/sbin/vsftpd /etc/cociber-ftp/vsftpd.conf
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now cociber-ftp.service
sudo systemctl status cociber-ftp.service --no-pager
sudo journalctl -u cociber-ftp.service -n 30 --no-pager
sudo ss -lntp '( sport = :21 )'
```

Esperado: unidad activa estable y escucha en `10.10.30.21:21`. Los puertos pasivos se abren durante una transferencia, no todos permanentemente. Si la unidad reinicia, deténla con `sudo systemctl stop cociber-ftp.service` y corrige el error del registro antes de reiniciar.

## 6. Comprobar el firewall del destino

En SRVFSAD:

```bash
sudo ufw status verbose
sudo nft list ruleset
```

El router ya permite VLAN20→VLAN30; no agregues DNAT ni salida a Internet para FTP. Si **UFW está activo** y es el firewall que administra esta VM, permite a las Kali preparadas conectar al control y al rango de datos:

```bash
for kali_ip in 10.10.20.10 10.10.20.11 10.10.20.12; do
  sudo ufw allow from "$kali_ip" to 10.10.30.21 port 21 proto tcp
  sudo ufw allow from "$kali_ip" to 10.10.30.21 port 30000:30009 proto tcp
done
sudo ufw status numbered
```

Si UFW está inactivo, no lo actives en una sesión remota sin preparar primero las reglas administrativas. Si se usa nftables directamente, entrega al responsable los mismos orígenes y puertos para incorporarlos al conjunto vigente, sin hacer `flush ruleset`. Revisa reglas más amplias existentes: permitir estas IP no elimina accesos ya concedidos.

## 7. Descargar desde Kali y comprobar integridad

En la terminal de **Kali**, comprueba `command -v curl`. Si no existe, el instructor debe instalarlo desde el repositorio aprobado antes de la demo (`sudo apt-get install curl`). Ejecuta:

```bash
curl --fail --connect-timeout 5 --max-time 30 --ftp-pasv --user ctf_ftp_demo ftp://10.10.30.21/
curl --fail --connect-timeout 5 --max-time 30 --ftp-pasv --user ctf_ftp_demo ftp://10.10.30.21/evidencia.txt --output evidencia-ftp.txt
cat evidencia-ftp.txt
sha256sum evidencia-ftp.txt
```

Curl solicitará la contraseña: no escribas `usuario:contraseña` en el comando. El texto esperado es `EVIDENCIA_FTP: descarga de laboratorio correcta`. En SRVFSAD compara:

```bash
sudo sha256sum /srv/cociber-ftp/ctf_ftp_demo/evidencia.txt
```

Los hashes deben ser iguales. Prueba también desde Kali que el login SSH de esa cuenta no funciona:

```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1 ctf_ftp_demo@10.10.30.21
```

Debe rechazar la autenticación. Verifica previamente la huella del host; no desactives StrictHostKeyChecking.

| Error | Revisar |
| --- | --- |
| Connection refused | Unidad cociber-ftp y escucha en 21 |
| Timeout al listar o descargar | Rango pasivo 30000–30009, dirección anunciada y firewall; abrir solo 21 no basta |
| 530 Login incorrect | Contraseña, cuenta activa, lista de usuarios y PAM; no pruebes con la cuenta administrativa |
| Refusing to run with writable root inside chroot | Raíz de la cuenta debe pertenecer a root sin escritura del jugador |
| 550 al descargar | Nombre del archivo, permisos de lectura y grupo |

## 8. Cerrar el ensayo

Cierra los clientes FTP. En SRVFSAD:

```bash
sudo systemctl stop cociber-ftp.service
sudo passwd -l ctf_ftp_demo
```

El servicio detenido corta sus sesiones; bloquear la contraseña por sí solo no equivale a cerrarlas. Conserva configuración y evidencia hasta registrar el resultado. Para repetir este ensayo, usa `sudo passwd -u ctf_ftp_demo` y `sudo systemctl start cociber-ftp.service` solo si sigue siendo la cuenta dedicada de prueba. La reversión completa puede realizarse mediante el snapshot previo, después de confirmar que la VM no tiene corridas.

Siguiente: [12. Validación e integración](12_VALIDACION_WINDOWS_FTP.md).
