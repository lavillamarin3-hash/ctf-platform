# 03. Preparar LAB-LNXVICT para ESC-02

**Antes:** archivos en `/tmp`, labops probado por clave y snapshot previo: [01](01_REQUISITOS_Y_TRANSFERENCIA.md) y [02](02_CUENTA_TECNICA_Y_CLAVES.md). Esta guía modifica solo LAB-LNXVICT, `10.10.30.12`.

## 1. Abrir la sesión correcta

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
```

En la VM:

```bash
hostname
sudo ss -lntp '( sport = :2222 )'
sudo groupadd -f cociber-ssh
sudo install -o root -g root -m 0755 /tmp/ctf-lab-helper.py /usr/local/sbin/ctf-ssh-lab
sudo python3 -m py_compile /usr/local/sbin/ctf-ssh-lab
```

La compilación correcta no muestra errores. Si 2222 ya está ocupado, identifica su servicio anterior y coordina la sustitución tras limpiar las corridas. No arranques una segunda instancia ni mates un proceso desconocido por el puerto.

## 2. Instalar la instancia didáctica

```bash
sudo install -o root -g root -m 0644 /tmp/sshd-practice.conf /etc/ssh/sshd-practice.conf
sudo install -o root -g root -m 0644 /tmp/cociber-sshd.service /etc/systemd/system/cociber-sshd.service
sudo /usr/sbin/sshd -t -f /etc/ssh/sshd-practice.conf
```

Sin salida significa configuración sintácticamente válida. El archivo didáctico escucha exclusivamente en `10.10.30.12:2222`, admite el grupo `cociber-ssh` y bloquea root y forwarding.

## 3. Separar el acceso didáctico del administrativo

Mantén esta sesión abierta. Revisa la configuración efectiva del SSH **administrativo**:

```bash
sudo /usr/sbin/sshd -T | grep -E '^(port|denygroups|allowgroups|allowusers) '
sudo cp -a /etc/ssh/sshd_config "/etc/ssh/sshd_config.antes-cociber.$(date -u +%Y%m%dT%H%M%S).bak"
sudo nano /etc/ssh/sshd_config
```

En la sección global, antes de cualquier bloque `Match`, incorpora `DenyGroups cociber-ssh`. Si ya existe DenyGroups, conserva sus grupos y añade `cociber-ssh`; revisa también los archivos Include. **No añadas este rechazo a `sshd-practice.conf`**, que debe permitir ese grupo.

Valida antes de recargar:

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | grep '^denygroups '
sudo systemctl status ssh.service --no-pager
```

Debe aparecer `cociber-ssh` entre los grupos denegados. Si hay error o la unidad real no es `ssh.service`, detente y confirma la configuración con el administrador. En la instalación con `ssh.service` activa:

```bash
sudo systemctl reload ssh.service
```

Abre **otra ventana PowerShell** y repite el SSH del paso 1. Confirma que entra y ejecuta `hostname`. Solo después cierra la sesión anterior. Así compruebas que no perdiste el acceso de mantenimiento.

## 4. Dar sudo únicamente al helper

En LNXVICT:

```bash
sudo EDITOR=nano visudo -f /etc/sudoers.d/cociber-fresh
```

Escribe una línea:

```sudoers
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-ssh-lab create *, /usr/local/sbin/ctf-ssh-lab check *, /usr/local/sbin/ctf-ssh-lab destroy *
```

Guarda con Ctrl+O, Enter y Ctrl+X. Después:

```bash
sudo chmod 0440 /etc/sudoers.d/cociber-fresh
sudo visudo -cf /etc/sudoers.d/cociber-fresh
sudo -u labops sudo -n -l
```

Debe indicar análisis correcto y permitir las tres acciones sin contraseña. No concedas `python3 *` ni acceso general a shell como root.

## 5. Iniciar y comprobar

Con el puerto libre y la administración validada:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cociber-sshd.service
sudo systemctl status cociber-sshd.service --no-pager
sudo ss -lntp '( sport = :2222 )'
```

Esperado: unidad activa y escucha en `10.10.30.12:2222`. No crees cuentas débiles manualmente: el helper genera una por corrida y la elimina al cerrar. La contraseña del usuario administrativo no es parte del diccionario de práctica.

Siguiente: [04. Kali](04_KALI_SESIONES.md).
