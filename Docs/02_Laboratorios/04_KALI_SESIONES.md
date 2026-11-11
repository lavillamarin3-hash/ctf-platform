# 04. Preparar las sesiones de los jugadores en Kali

**Antes:** completa [01. Transferencia](01_REQUISITOS_Y_TRANSFERENCIA.md) y [02. Claves](02_CUENTA_TECNICA_Y_CLAVES.md). Repite esta guía en cada Kali que vayas a habilitar. Una Kali admite una corrida simultánea; para empezar basta LAB-KALI-BLUE (`10.10.20.12`). LAB-KALI-PURPLE es `10.10.20.11`.

## 1. Entrar a la Kali

Desde PowerShell local, para LAB-KALI-BLUE:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali-blue@10.10.20.12
```

Para LAB-KALI-PURPLE, abre otra ventana PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali-purple@10.10.20.11
```

Si preparas LAB-KALI, utiliza desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali@10.10.20.10
```

Introduce la contraseña de mantenimiento cuando se solicite. Son cuentas Linux de administración, distintas de los jugadores de CoCiber y de la cuenta técnica `labops`. En la VM elegida:

```bash
hostname
ip -brief address
id labops
ls -l /tmp/ctf-lab-helper.py
command -v python3 ssh nmap hydra
sudo systemctl status ssh.service --no-pager
```

No continúes si la IP no corresponde. Si faltan herramientas, el encargado debe instalarlas desde los repositorios de Kali antes de la demo. Con acceso a esos repositorios ya autorizado y operativo, el comando base es `sudo apt-get update` y después `sudo apt-get install python3 openssh-server openssh-client nmap hydra`. No cambies el firewall para obtener Internet sin revisar la política del laboratorio.

## 2. Instalar el helper y su permiso limitado

```bash
sudo groupadd -f cociber-kali
sudo install -o root -g root -m 0755 /tmp/ctf-lab-helper.py /usr/local/sbin/ctf-kali-session
sudo python3 -m py_compile /usr/local/sbin/ctf-kali-session
sudo EDITOR=nano visudo -f /etc/sudoers.d/cociber-fresh
```

Escribe esta línea completa, guarda con Ctrl+O, Enter y Ctrl+X:

```sudoers
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-kali-session create *, /usr/local/sbin/ctf-kali-session check *, /usr/local/sbin/ctf-kali-session destroy *
```

Comprueba:

```bash
sudo chmod 0440 /etc/sudoers.d/cociber-fresh
sudo visudo -cf /etc/sudoers.d/cociber-fresh
sudo -u labops sudo -n -l
```

Esperado: sintaxis correcta y permiso para esas tres acciones. El script debe pertenecer a root y no ser modificable por labops. No agregues a labops ni a `cociber-kali` al grupo sudo.

## 3. Verificar el acceso SSH de las cuentas temporales

La plataforma crea un usuario `ctf_<run_id>` con contraseña aleatoria y lo conecta por SSH al puerto 22. Revisa las reglas efectivas, incluidos los bloques Match:

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | grep -E '^(port|passwordauthentication|authenticationmethods|allowgroups|denygroups|allowusers|denyusers) '
```

Debe poder autenticarse por contraseña una cuenta del grupo `cociber-kali`. Si hay listas AllowGroups/AllowUsers o Match, pide al administrador ajustar específicamente ese grupo conservando las reglas de administración. Para editar, el comando base es `sudo nano /etc/ssh/sshd_config`; valida con `sudo /usr/sbin/sshd -t` antes de `sudo systemctl reload ssh.service`. Conserva una sesión administrativa abierta y prueba una segunda conexión antes de cerrarla.

No apliques aquí el `DenyGroups cociber-ssh` de LNXVICT ni copies su configuración del puerto 2222. La prueba piloto de [07](07_GRUPOS_RETOS_Y_PILOTO.md) verificará la contraseña de la cuenta realmente creada; la lectura de configuración por sí sola no acredita una sesión.

## 4. Comprobar la ruta hacia las víctimas

Desde esta Kali, después de preparar cada víctima:

```bash
nmap -Pn -sT -p 2222 10.10.30.12
nmap -Pn -sT -p 80 10.10.30.20
```

El puerto correspondiente debe aparecer abierto. Para ESC-03 hace falta además un navegador **dentro de Kali** y una sesión gráfica ya probada. La consola integrada del reto es SSH: no muestra un escritorio. Prepara el acceso gráfico según [Guacamole y conexiones](../01_Plataforma/03_GUACAMOLE_Y_CONEXIONES.md). No publiques ESC-03 hasta resolver este requisito.

Siguiente: [05. LAB-SRVWEB y DVWA](05_SRVWEB_DVWA.md). Si harás únicamente ESC-02, pasa a [06. Pruebas y worker](06_PRUEBAS_Y_WORKER.md), manteniendo DVWA deshabilitado.
