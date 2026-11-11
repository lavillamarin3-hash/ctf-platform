# 01. Requisitos y transferencia a las VM

**Antes:** termina [inventario y catálogo](../01_Plataforma/04_INVENTARIO_Y_CATALOGO.md). Necesitas acceso de mantenimiento a LNXVICT, SRVWEB y al menos una Kali; para la demo completa se recomienda preparar Blue y Purple. Las contraseñas de mantenimiento no se escriben en estos documentos.

## 1. Acordar la ventana y guardar snapshots

En la plataforma, comprueba que las VM no tengan corridas vivas. Si vienen de la instalación anterior, ciérralas y espera su limpieza antes de reemplazar servicios. El responsable de Nutanix debe guardar un snapshot identificado de cada VM que se modificará. Anota nombre, fecha y VM; no basta con escribir un nombre de snapshot que aún no existe.

Mantén una sesión SSH administrativa abierta mientras cambias SSH y valida otra conexión antes de cerrarla. El puerto 22 es de mantenimiento; el ejercicio de fuerza bruta utiliza 2222.

## 2. Comprobar los archivos en LAB-CTFWEB

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

Dentro del servidor web:

```bash
cd /ctf-plataform/ || exit 1
ls -l labs/fresh/helpers/ctf-lab-helper.py labs/fresh/helpers/sshd-practice.conf labs/fresh/helpers/cociber-sshd.service
sha256sum labs/fresh/helpers/ctf-lab-helper.py
```

Si no están, actualiza el código según [la guía de plataforma](../01_Plataforma/02_ACTUALIZAR_INTERFAZ_Y_GUACAMOLE.md). No descargues un helper diferente para completar el paso.

## 3. Transferir desde LAB-CTFWEB a las víctimas

Ejecuta en la misma sesión del servidor web; se usa la ruta directa VLAN10 → VLAN30:

```bash
scp labs/fresh/helpers/ctf-lab-helper.py labs/fresh/helpers/sshd-practice.conf labs/fresh/helpers/cociber-sshd.service lab-lnxvict@10.10.30.12:/tmp/
scp labs/fresh/helpers/ctf-lab-helper.py lab-srvweb@10.10.30.20:/tmp/
```

SSH/SCP pedirá la contraseña correspondiente. Copiar los archivos todavía no instala ni activa los servicios.

## 4. Transferir a Kali

Las cuentas administrativas confirmadas son:

| VM | IP | Usuario Linux / hostname |
| --- | --- | --- |
| LAB-KALI-BLUE | 10.10.20.12 | `lab-kali-blue` |
| LAB-KALI-PURPLE | 10.10.20.11 | `lab-kali-purple` |
| LAB-KALI | 10.10.20.10 | `lab-kali` |

Ejecuta en la terminal de **LAB-CTFWEB**, no en PowerShell local. Primero entra en la carpeta del proyecto:

```bash
cd /ctf-plataform/ || exit 1
```

Para **LAB-KALI-BLUE**:

```bash
scp labs/fresh/helpers/ctf-lab-helper.py lab-kali-blue@10.10.20.12:/tmp/ctf-lab-helper.py
```

Para **LAB-KALI-PURPLE**, si también la vas a preparar:

```bash
scp labs/fresh/helpers/ctf-lab-helper.py lab-kali-purple@10.10.20.11:/tmp/ctf-lab-helper.py
```

Para **LAB-KALI**, si la vas a utilizar:

```bash
scp labs/fresh/helpers/ctf-lab-helper.py lab-kali@10.10.20.10:/tmp/ctf-lab-helper.py
```

Cuando SCP solicite la contraseña, introduce la de mantenimiento de la Kali de destino; no se muestra mientras la escribes. En la primera conexión verifica la huella con el responsable antes de aceptarla. Espera a que cada copia termine sin errores antes de continuar. Ya no necesitas `read` ni `unset`: cada comando incluye su usuario confirmado.

## 5. Revisar cada destino

Abre SSH a cada VM según [comandos base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). En ella:

```bash
hostname
cat /etc/os-release
command -v python3
command -v sshd
ls -l /tmp/ctf-lab-helper.py
sha256sum /tmp/ctf-lab-helper.py
```

El hash debe coincidir con el del servidor web. Si falta Python3 u OpenSSH Server, solicita al administrador instalar esos paquetes para la distribución real. La red no garantiza salida permanente a Internet; no cambies rutas ni descargues paquetes de otra distribución.

El mismo archivo se instalará con tres nombres: `ctf-ssh-lab` en LNXVICT, `ctf-dvwa-lab` en SRVWEB y `ctf-kali-session` en Kali. Ese nombre determina su comportamiento. No sustituye los helpers históricos `ctf-dvwa-flag` ni `ctf-ssh-practice.py`.

Siguiente: [02. Cuenta técnica y claves](02_CUENTA_TECNICA_Y_CLAVES.md).
