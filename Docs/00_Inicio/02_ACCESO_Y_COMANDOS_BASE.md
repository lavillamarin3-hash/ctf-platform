# 02. Acceso y comandos base

**Requisito:** equipo conectado a la red de administración `10.195.20.0/24`, acceso autorizado al router y credenciales de mantenimiento. Las contraseñas se introducen cuando SSH las solicite; no aparecen al escribir y no se guardan en las guías.

## 1. Abrir una terminal en Windows

Abre Inicio, escribe **PowerShell** y abre la aplicación. Comprueba que el cliente SSH esté disponible:

```powershell
ssh -V
```

Si Windows indica que el comando no existe, solicita habilitar **Cliente OpenSSH** en Características opcionales de Windows. No necesitas instalar un servidor SSH en tu equipo.

## 2. Entrar al servidor web

Desde **PowerShell local**:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

La cuenta `lab-ctfweb` es la utilizada en las sesiones anteriores. Si fue cambiada, usa la cuenta Linux real facilitada por el responsable. En el primer acceso verifica la huella SSH con él antes de aceptarla. SSH puede pedir primero la clave del router y después la del servidor.

Ahora estás en una terminal **Linux del servidor web**. Ejecuta:

```bash
hostname
whoami
cd /home/lab-ctfweb/ctf-platform || exit 1
pwd
ls -l deploy/docker-compose.fresh.yml
test -f .env.fresh && echo 'Existe la configuración privada'
```

`pwd` debe mostrar el checkout real: las últimas sesiones utilizan `/home/lab-ctfweb/ctf-platform`. Las primeras guías usaban `/ctf-plataform`; sustituye esa ruta cuando corresponda. Si la carpeta no existe, comprueba la ruta y los dos archivos anteriores; no crees otra carpeta para continuar. `cd` cambia la carpeta de la sesión, no mueve archivos.

Para ejecutar operaciones administrativas, antepone `sudo` al comando indicado. Su contraseña es la de la cuenta Linux de esa VM, no la de `admin_ctf`, PostgreSQL o Redis.

## 3. Abrir sesiones de las víctimas desde el equipo local

En **otra ventana PowerShell**:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
```

Para el servidor web vulnerable:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
```

Dentro de cada sesión, comprueba `hostname` antes de ejecutar instrucciones. No ejecutes `cd /ctf-plataform/` en estas víctimas: el proyecto completo vive en LAB-CTFWEB; a las víctimas se transfieren archivos concretos a `/tmp`.

## 4. Acceder a Kali y al servidor de datos

Desde **PowerShell local**, utiliza el comando de la Kali a la que vas a entrar. Para LAB-KALI-BLUE:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali-blue@10.10.20.12
```

Para LAB-KALI-PURPLE, en otra ventana PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali-purple@10.10.20.11
```

Para LAB-KALI, en otra ventana PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali@10.10.20.10
```

Introduce las contraseñas cuando SSH las solicite. En la VM, ejecuta `hostname` y `whoami`: deben corresponder a `lab-kali-blue`, `lab-kali-purple` o `lab-kali`, respectivamente.

La cuenta Linux de **LAB-DB-POSTGRES** todavía debe confirmarse. Solicita su nombre real y escríbelo en el prompt desde PowerShell local:

```powershell
$CuentaBD = Read-Host 'Cuenta Linux administrativa de LAB-DB-POSTGRES'
ssh -J lab-rtrfw@10.195.20.20 "$($CuentaBD)@10.10.10.14"
```

`cociberctf` y `cociber_app` son cuentas de los motores, no cuentas Linux confirmadas. La administración de BD no forma parte de la preparación normal de los laboratorios cuando la plataforma ya conecta correctamente.

## 5. Pasar de LAB-CTFWEB a una víctima

También puedes ejecutar SSH y SCP desde LAB-CTFWEB hacia VLAN20/30, porque VLAN10 tiene acceso administrativo. En ese caso **no se necesita el salto de gestión**:

```bash
ssh lab-lnxvict@10.10.30.12
```

Cuando termines, `exit` vuelve a la terminal desde la que abriste SSH. Ejecuta `hostname` para saber si has vuelto al servidor web o al equipo local.

## 6. Editar, copiar comandos y verificar

En LAB-CTFWEB, para editar configuración:

```bash
cd /home/lab-ctfweb/ctf-platform || exit 1
nano .env.fresh
```

Si el archivo pertenece a root, usa `sudo nano .env.fresh`. En Nano: **Ctrl+O**, Enter para guardar y **Ctrl+X** para salir. En sudoers utiliza siempre `sudo EDITOR=nano visudo -f RUTA`, seguido de la validación indicada.

No imprimas `.env.fresh` ni compartas su contenido. Para comprobar Docker sin revelar valores:

```bash
cd /home/lab-ctfweb/ctf-platform || exit 1
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
```

Si no hay salida y el comando termina correctamente, la configuración es válida. No implica que las VM o los motores estén accesibles.

Los bloques `bash` se ejecutan en Linux; los bloques `powershell`, en Windows. Los bloques `sql`, `sudoers`, `ini` o `dotenv` son contenido para el programa/archivo indicado, no comandos para pegar directamente en Bash. Cuando una guía utiliza `<<'SQL'` o `<<'PY'`, copia **todo el bloque**, incluida la línea final.

En un comando dividido por `\`, la barra debe ser el último carácter de la línea. Si te resulta más fácil, copia los comandos Docker que estas guías proporcionan en una sola línea. Ctrl+C interrumpe una orden que sigue ejecutándose; no lo uses para omitir una comprobación sin investigar.

Siguiente: [verificar la plataforma existente](../01_Plataforma/01_VERIFICAR_PLATAFORMA_EXISTENTE.md).
