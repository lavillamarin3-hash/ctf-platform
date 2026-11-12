# 06. Conectar escritorios por Guacamole: router, Windows y Kali

Contexto actualizado el **12 de noviembre de 2026**. LAB-RTRFW usa Ubuntu Server 26.04. IP pública de CTF declarada ahora: **10.195.20.56:443**, con DNAT hacia **10.10.10.13:443**. Guacamole mantiene su dirección interna **10.10.10.10**.

## 1. Qué permiten ya las reglas recibidas

**Caso confirmado:** Guacamole y guacd 1.6.0 están en Docker Compose con MariaDB 11.4; falla RDP hacia LAB-KALI-BLUE. Sigue primero [08. Diagnóstico específico de Kali Blue y Docker](08_KALI_BLUE_RDP_DOCKER.md). Esta guía conserva el diagnóstico general de router, Windows y Kali.

Estas dos reglas de `forward` permiten todos los puertos desde VLAN10 hacia VLAN20/30, incluido TCP 3389:

```text
ip saddr 10.10.10.0/24 ip daddr 10.10.20.0/24 accept
ip saddr 10.10.10.0/24 ip daddr 10.10.30.0/24 accept
```

`ct state established,related accept` permite las respuestas. **Si el router ve como origen 10.10.10.10 y esas reglas están cargadas, no falta una regla RDP en este router.** No abras 3389 en `input`: esa cadena corresponde al propio router. Tampoco necesitas DNAT de RDP desde gestión, ni permitir nuevas conexiones de VLAN20/30 hacia VLAN10.

El navegador habla con Guacamole; **guacd** abre la conexión RDP hacia la VM. El recorrido esperado es:

```text
Navegador → aplicación Guacamole → guacd → LAB-RTRFW → VM:3389
                                      origen esperado: 10.10.10.10
```

La arquitectura está descrita en la [documentación de Apache](https://guacamole.apache.org/doc/gug/guacamole-architecture.html). «Probar puerto» en CoCiber sale de la API 10.10.10.13 y no sustituye una prueba desde guacd.

## 2. Comprobar el router sin cambiar sus reglas

Desde PowerShell local, abre una sesión:

```powershell
ssh lab-rtrfw@10.195.20.20
```

Si no entra, usa **la consola de LAB-RTRFW en Nutanix**. El archivo recibido ya no incluye la excepción SSH por ens9 de la configuración anterior: una conexión existente puede continuar, aunque las nuevas fallen. En el router:

```bash
hostname
ip -br address
ip route
sysctl net.ipv4.ip_forward
sudo nft -a list chain inet lab_firewall forward
sudo nft -a list chain inet lab_firewall input
```

Debe aparecer `net.ipv4.ip_forward = 1`. Revisa que las reglas activas coincidan con el archivo; leer `/etc/nftables.conf` no acredita que se haya aplicado. Confirma `.56` en ens9 o su mecanismo de entrega de IP; cambiar `define CTF_PUB` no asigna la IP a la interfaz.

Para conservar el acceso de administración por la red autorizada, si la regla falta, añádela desde la consola Nutanix:

```bash
sudo nft insert rule inet lab_firewall input iifname "ens9" ip saddr 10.195.20.0/24 tcp dport 22 counter accept
```

Prueba **otra** sesión SSH antes de cerrar la consola. Después respalda y edita el archivo para conservar la regla:

```bash
sudo cp -a /etc/nftables.conf "/etc/nftables.conf.$(date -u +%Y%m%dT%H%M%S).bak"
sudo nano /etc/nftables.conf
```

Dentro de `chain input`, después de las reglas de estado, añade una sola vez:

```text
iifname "ens9" ip saddr 10.195.20.0/24 tcp dport 22 counter accept
```

Guarda con Ctrl+O, Enter y Ctrl+X. Valida sin aplicar:

```bash
sudo nft -c -f /etc/nftables.conf
```

Si la sintaxis falla, corrige antes de recargar. El texto original del chat tiene barras y entidades HTML de copiado: el archivo debe contener líneas normales, sin `\` al final de cada línea ni `&#x20;`. No reemplaces todo el archivo por una copia escapada del chat. La regla temporal ya funciona; una recarga completa con `flush ruleset` elimina también entradas dinámicas como `internet_switch`. Programa esa recarga fuera de las prácticas, con la consola Nutanix abierta. No hace falta recargar para diagnosticar RDP.

## 3. Comprobar por dónde sale LAB-GUAC

Entra a LAB-GUAC mediante su acceso administrativo habitual. Su cuenta Linux no está confirmada; no confundas una cuenta web de Guacamole con una cuenta Linux. Desde PowerShell puedes usar:

```powershell
$cuentaGuac = Read-Host 'Cuenta Linux administrativa de LAB-GUAC'
ssh -J lab-rtrfw@10.195.20.20 "$($cuentaGuac)@10.10.10.10"
```

En LAB-GUAC:

```bash
hostname
ip -br address
ip route get 10.10.20.12
ip route get 10.10.30.10
command -v nc
sudo systemctl status guacd --no-pager
sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Si guacd es nativo, Docker puede no estar instalado; si está en Docker, la unidad nativa puede no existir. Identifica la modalidad antes de continuar. Las rutas esperadas usan la interfaz interna, gateway **10.10.10.1** y origen **10.10.10.10**. LAB-GUAC tenía además una interfaz de gestión `.22`; si sale por gestión, no coincide con la regla VLAN10→laboratorios.

**Solo si las rutas son incorrectas**, confirma el nombre real de la interfaz que tiene 10.10.10.10 y añade rutas específicas en LAB-GUAC:

```bash
read -rp 'Interfaz interna de LAB-GUAC que tiene 10.10.10.10: ' guac_if
ip -br address show dev "$guac_if"
```

Verifica visualmente esa IP antes del siguiente bloque:

```bash
sudo ip route replace 10.10.20.0/24 via 10.10.10.1 dev "$guac_if" src 10.10.10.10
sudo ip route replace 10.10.30.0/24 via 10.10.10.1 dev "$guac_if" src 10.10.10.10
ip route get 10.10.20.12
ip route get 10.10.30.10
unset guac_if
```

Son rutas temporales: si resuelven el problema, intégralas en la configuración de red vigente de LAB-GUAC, conservando su acceso de gestión. No cambies la ruta por defecto ni sobrescribas un Netplan sin revisar el archivo real.

## 4. Probar desde el origen real de RDP

En LAB-GUAC, si `nc` no existe, instala `netcat-openbsd` desde el repositorio aprobado. Para guacd nativo:

```bash
nc -vz -w 3 10.10.20.12 3389
nc -vz -w 3 10.10.30.10 3389
nc -vz -w 3 10.10.30.11 3389
```

Prueba únicamente las VM que has preparado para RDP. Para **guacd en Docker**, toma el nombre exacto de `docker ps`, consulta solo metadatos de red y prueba su espacio de red con las herramientas del host:

```bash
read -rp 'Nombre exacto del contenedor guacd: ' guacd_container
sudo docker inspect --format '{{.HostConfig.NetworkMode}} {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$guacd_container"
guacd_pid=$(sudo docker inspect --format '{{.State.Pid}}' "$guacd_container")
if [ "$guacd_pid" -gt 0 ] 2>/dev/null; then
  sudo nsenter -t "$guacd_pid" -n ip route get 10.10.20.12
  sudo nsenter -t "$guacd_pid" -n nc -vz -w 3 10.10.20.12 3389
  sudo nsenter -t "$guacd_pid" -n nc -vz -w 3 10.10.30.10 3389
else
  echo 'El contenedor no está en ejecución; revisar antes de probar.'
fi
```

El NAT de Docker puede cambiar el origen al salir del host. Si el host conecta y el contenedor no, revisa sus rutas, el reenvío/NAT del host y las reglas Docker; no abras redes de contenedores arbitrarias en LAB-RTRFW como primera solución.

En otra terminal del **router**, durante un único intento de conexión, observa las cabeceras:

```bash
sudo tcpdump -ni any -c 30 'tcp port 3389 and (host 10.10.20.12 or host 10.10.30.10 or host 10.10.30.11)'
```

Si no llegan paquetes, el problema está antes del router. Un SYN que sale hacia la víctima sin respuesta exige revisar servicio, firewall local y ruta de retorno. Un RST suele indicar rechazo activo/puerto sin servicio. SYN/SYN-ACK y fallo posterior orientan a RDP, TLS o credenciales; no prueban por sí solos que el escritorio funcione. Usa Ctrl+C si no se alcanzan 30 paquetes.

## 5. Preparar Windows 10 Pro A/B

En la consola Nutanix de la Windows correspondiente, inicia sesión con `lab-winvict-a` o `lab-winvict-b`. Abre **Configuración → Sistema → Escritorio remoto**, habilítalo y conserva **NLA**. Windows Pro puede alojar RDP; la cuenta debe tener permiso de acceso remoto. [Referencia de Microsoft](https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/remotepc/remote-desktop-allow-access).

En PowerShell como administrador de **esa VM**:

```powershell
hostname
Get-Service TermService
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections
Get-NetTCPConnection -State Listen -LocalPort 3389
Get-NetIPConfiguration
```

Esperado: servicio activo, `fDenyTSConnections = 0`, escucha en 3389 y retorno mediante 10.10.30.1. Si una política de dominio impide habilitarlo, resuélvela con el responsable; no desactives NLA para ocultar un error de contraseña.

Si necesitas permitir TCP3389 en Windows y confirmaste que guacd llega como 10.10.10.10, revisa primero si ya existe la regla dedicada:

```powershell
Get-NetFirewallRule -Name 'CoCiber-RDP-Guacamole' -ErrorAction SilentlyContinue
```

Solo si no existe:

```powershell
New-NetFirewallRule -Name 'CoCiber-RDP-Guacamole' -DisplayName 'CoCiber RDP desde Guacamole' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3389 -RemoteAddress 10.10.10.10 -Profile Any
```

Una regla nueva no anula permisos más amplios ni bloqueos explícitos. Revisa también las reglas existentes y las políticas aplicadas. No apagues Windows Firewall. La comprobación básica aquí utiliza TCP; no necesitas publicar UDP3389 en el router para efectuarla.

Para la prueba administrativa en Guacamole: protocolo RDP, IP de A/B, puerto 3389, usuario `lab-winvict-a` / `lab-winvict-b` y dominio local `lab-winvict-a` / `lab-winvict-b`. Introduce la contraseña de la cuenta, no un PIN. No compartas conexiones administrativas con jugadores. Para una cuenta de práctica existente, añádela al grupo local Usuarios de escritorio remoto, identificado por SID para evitar problemas de idioma:

```powershell
$cuentaRdp = Read-Host 'Nombre de la cuenta LOCAL de práctica ya creada en esta VM'
Get-LocalUser -Name $cuentaRdp -ErrorAction Stop
Add-LocalGroupMember -Group (Get-LocalGroup -SID 'S-1-5-32-555') -Member "$env:COMPUTERNAME\$cuentaRdp"
```

Ejecuta ese bloque solo si la práctica necesita escritorio en esa Windows. No implica pertenencia a Administradores ni elimina otras restricciones de inicio de sesión.

## 6. Preparar Kali para una práctica gráfica

SSH funciona aunque no exista escritorio remoto. En la **Kali elegida**, con su cuenta administrativa (`lab-kali-blue`, `lab-kali-purple` o `lab-kali`):

```bash
hostname
command -v startxfce4
sudo systemctl status xrdp xrdp-sesman --no-pager
sudo ss -lntp '( sport = :3389 )'
```

Si faltan escritorio/servidor y la VM tiene acceso autorizado al repositorio, instala:

```bash
sudo apt-get update
sudo apt-get install kali-desktop-xfce xorg xrdp xorgxrdp
sudo systemctl enable --now xrdp
sudo systemctl status xrdp xrdp-sesman --no-pager
sudo ss -lntp '( sport = :3389 )'
```

Se conserva **3389**: la receta oficial de Kali muestra también un ejemplo en 3390 para otros entornos; no copies ese cambio porque el módulo CoCiber admite RDP3389. [Paquetes y escritorio Xfce según Kali](https://www.kali.org/docs/general-use/xfce-with-rdp/).

Comprueba `sudo ufw status`; si UFW está activo y administra el firewall de esa Kali, permite el origen observado:

```bash
sudo ufw allow from 10.10.10.10 to any port 3389 proto tcp
```

No actives UFW a ciegas sobre la sesión administrativa. Si hay otro firewall local, incorpora ese flujo en su configuración real. En Guacamole elige RDP, IP de la Kali, 3389, cuenta local y dominio vacío. Para xrdp utiliza negociación compatible/TLS, sin exigir NLA de Windows. Los ajustes avanzados de seguridad y certificados se realizan en la administración nativa de Guacamole; el formulario CoCiber actual expone los campos básicos.

Si entra y se cierra o queda negro, revisa el escritorio y los registros antes de modificar el router:

```bash
sudo journalctl -u xrdp -u xrdp-sesman --since '10 minutes ago' --no-pager
sudo tail -n 60 /var/log/xrdp.log /var/log/xrdp-sesman.log
```

Prueba con una cuenta de escritorio dedicada y sin una sesión gráfica local simultánea. No cambies las cuentas temporales `ctf_*` ni sus archivos mientras exista una corrida. La consola automática de la plataforma sigue siendo SSH; instalar xrdp no la convierte en un escritorio RDP automático.

## 7. Si TCP funciona, revisar el error de Guacamole

Reproduce una vez el fallo y anota hora, IP destino y nombre de conexión. Para guacd nativo:

```bash
sudo journalctl -u guacd --since '10 minutes ago' --no-pager
```

Para Docker, en la sesión donde definiste `guacd_container`:

```bash
sudo docker logs --since 10m --tail 100 "$guacd_container"
unset guacd_container guacd_pid
```

| Mensaje/resultado | Siguiente revisión |
| --- | --- |
| Connection refused | Puerto correcto y servicio RDP/xrdp escuchando |
| Timeout | Ruta efectiva, origen observado, firewall local y retorno |
| Authentication / logon failure | Cuenta, contraseña, dominio local y permiso RDP |
| Certificate validation failed | Identidad del certificado y confianza TLS en el entorno de guacd |
| Security negotiation failed | Windows/NLA frente a xrdp/TLS y versiones compatibles |
| Sin conexión a guacd | Tramo aplicación Guacamole→guacd, generalmente TCP4822 interno |
| Conecta pero no dibuja escritorio | Registros de sesión y túnel/proxy web |

No establezcas `ignore-cert=true` como arreglo general. Verifica el certificado del servidor y configura confianza/nombre compatibles en guacd; los certificados autofirmados de RDP/xrdp requieren atender esa confianza. Los parámetros se describen en [configuración RDP de Apache](https://guacamole.apache.org/doc/gug/configuring-guacamole.html), y los registros/túneles en [diagnóstico de Apache](https://guacamole.apache.org/doc/gug/troubleshooting.html).

Comparte el error concreto y las salidas de rutas, escucha y prueba TCP, ocultando contraseñas y tokens. Con esas evidencias se decide si hace falta cambiar rutas, servicio o parámetros RDP. Las reglas recibidas por sí solas no demuestran que el router sea la causa.
