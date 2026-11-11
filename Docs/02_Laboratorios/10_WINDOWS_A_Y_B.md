# 10. Windows 10 Pro: LAB-WINVICT-A y LAB-WINVICT-B

**Antes:** completa [09. Preparación](09_PREPARACION_WINDOWS_Y_FTP.md). Esta es una prueba manual de acceso SSH y lectura SMB A→B. No habilita aún ESC-04 en la plataforma.

## 1. Verificar sistema y dominio en ambas Windows

Desde la consola Nutanix de **cada VM**, inicia sesión con `lab-winvict-a\lab-winvict-a` en A y `lab-winvict-b\lab-winvict-b` en B, usando la contraseña administrativa recibida por separado. Abre Inicio, busca **Windows PowerShell**, pulsa «Ejecutar como administrador». Acepta la elevación con la cuenta correspondiente. Usa PowerShell de 64 bits. Ejecuta:

```powershell
hostname
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, CsName, CsDomain, CsPartOfDomain
Get-NetIPConfiguration
$PSVersionTable.PSVersion
$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
([Security.Principal.WindowsPrincipal]::new($identidad)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

Esperado: Windows 10 Pro, PowerShell 5.1 o posterior e IP `.10` en A / `.11` en B. La última consulta debe devolver `True`; si devuelve `False`, vuelve a abrir PowerShell elevado antes de instalar o cambiar permisos. `hostname` debe mostrar `lab-winvict-a` / `lab-winvict-b` (sin distinguir mayúsculas). No renombres equipos ni cambies IP si ya son correctos.

Si `CsPartOfDomain` es True, conserva la pertenencia al dominio y pide al responsable comprobar que las políticas permiten estas cuentas locales y reglas de laboratorio. No desunas el equipo ni cambies políticas de dominio. Los pasos siguientes describen cuentas **locales** y no crean usuarios de Active Directory.

## 2. Instalar SSH solamente en Windows A

En **A**, PowerShell como administrador. OpenSSH integrado requiere Windows 10 versión 1809 o posterior; compruébalo antes. [Requisitos e instalación oficiales de Microsoft](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).

```powershell
Get-WindowsCapability -Online -Name 'OpenSSH.Server*'
```

Si el estado ya es Installed, omite la instalación. Si es NotPresent y tienes acceso al origen de componentes aprobado:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

Si falla la descarga, conserva el código de error y solicita la capacidad correspondiente a la misma compilación. No descargues un instalador de otra versión para continuar. Después:

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
Get-Service sshd
Get-NetTCPConnection -State Listen -LocalPort 22
```

Esperado: `Running` y puerto 22 en escucha. Acota la regla de OpenSSH creada por Windows; si existe, conserva su nombre y cambia su alcance al laboratorio:

```powershell
if (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue) {
    Set-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -Enabled True -RemoteAddress '10.10.10.0/24','10.10.20.10','10.10.20.11','10.10.20.12','10.10.30.1'
} else {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'CoCiber SSH A' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 -RemoteAddress '10.10.10.0/24','10.10.20.10','10.10.20.11','10.10.20.12','10.10.30.1'
}
```

No desactives Windows Firewall. Anota el alcance anterior si esta regla ya atendía otro uso. Verifica la huella del servidor desde esta consola confiable:

```powershell
& "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe" -lf 'C:\ProgramData\ssh\ssh_host_ed25519_key.pub'
```

## 3. Crear la cuenta de entrada en A

Primero comprueba:

```powershell
Get-LocalUser -Name 'ctf_win_demo' -ErrorAction SilentlyContinue
```

Solo si no existe, crea la cuenta con una contraseña de prueba nueva, introducida de forma privada:

```powershell
$claveDemo = Read-Host 'Contraseña nueva para ctf_win_demo' -AsSecureString
New-LocalUser -Name 'ctf_win_demo' -Password $claveDemo -Description 'CoCiber ensayo manual Windows A'
$grupoUsuarios = Get-LocalGroup -SID 'S-1-5-32-545'
Add-LocalGroupMember -Group $grupoUsuarios -Member 'ctf_win_demo'
Remove-Variable claveDemo
```

Si la cuenta existe, revisa su propietario/uso antes de reutilizarla; no la sobrescribas. Comprueba que no pertenece a Administradores:

```powershell
$grupoAdministradores = Get-LocalGroup -SID 'S-1-5-32-544'
Get-LocalGroupMember -Group $grupoAdministradores
```

Desde **Kali**, abre una terminal:

```bash
ssh ctf_win_demo@10.10.30.10
```

Compara la huella con la obtenida en A antes de aceptarla. Introduce la contraseña de prueba. Si aparece un símbolo de sistema Windows, ejecuta `powershell -NoProfile`. Luego `hostname` y `whoami`: debes estar en A con `ctf_win_demo`. Deja esta sesión para el paso 6. Si no autentica, revisa en A `Get-WinEvent -LogName 'OpenSSH/Operational' -MaxEvents 20`; no debilites el acceso administrativo para permitir la práctica.

## 4. Crear cuenta y archivo de prueba en B

En **B**, PowerShell como administrador:

```powershell
hostname
Get-Service LanmanServer
Get-LocalUser -Name 'ctf_smb_demo' -ErrorAction SilentlyContinue
Get-SmbShare -Name 'COCIBER_DEMO' -ErrorAction SilentlyContinue
Test-Path -LiteralPath 'C:\CoCiberDemo'
```

`LanmanServer` debe estar Running. Si está detenido en esta VM dedicada, ejecuta `Start-Service LanmanServer` y vuelve a comprobarlo; si una política lo impide, resuelve esa dependencia antes de crear el recurso. Si existen la cuenta, el recurso o la carpeta, identifica su uso y conserva sus datos antes de continuar. El siguiente bloque es para una preparación nueva, con esos nombres libres:

```powershell
$ErrorActionPreference = 'Stop'
if ((Get-LocalUser -Name 'ctf_smb_demo' -ErrorAction SilentlyContinue) -or (Get-SmbShare -Name 'COCIBER_DEMO' -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath 'C:\CoCiberDemo')) { throw 'Ya existen recursos: revisar antes de continuar.' }
$claveDemo = Read-Host 'Contraseña nueva para ctf_smb_demo' -AsSecureString
New-LocalUser -Name 'ctf_smb_demo' -Password $claveDemo -Description 'CoCiber ensayo manual SMB B'
Add-LocalGroupMember -Group (Get-LocalGroup -SID 'S-1-5-32-545') -Member 'ctf_smb_demo'
Remove-Variable claveDemo
New-Item -ItemType Directory -Path 'C:\CoCiberDemo'
$cuentaLectura = "$env:COMPUTERNAME\ctf_smb_demo"
icacls 'C:\CoCiberDemo' /inheritance:r
if ($LASTEXITCODE -ne 0) { throw 'No se pudo retirar la herencia.' }
icacls 'C:\CoCiberDemo' /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "${cuentaLectura}:(OI)(CI)RX"
if ($LASTEXITCODE -ne 0) { throw 'No se pudo aplicar la ACL.' }
Set-Content -LiteralPath 'C:\CoCiberDemo\evidencia.txt' -Value 'EVIDENCIA_WINDOWS_A_B: lectura SMB correcta' -Encoding UTF8
New-SmbShare -Name 'COCIBER_DEMO' -Path 'C:\CoCiberDemo' -ReadAccess $cuentaLectura -EncryptData $true
Get-SmbShareAccess -Name 'COCIBER_DEMO'
icacls 'C:\CoCiberDemo'
```

La cuenta de práctica recibe lectura tanto en el recurso SMB como en NTFS. SYSTEM y Administradores conservan administración local. No se concede escritura a Everyone ni se habilita SMBv1. [Referencia de creación de recursos SMB](https://learn.microsoft.com/en-us/powershell/module/smbshare/new-smbshare).

## 5. Permitir SMB desde A a B

En **B**, confirma que el nombre de regla está libre antes de crearla:

```powershell
Get-NetFirewallRule -Name 'CoCiber-SMB-Desde-A' -ErrorAction SilentlyContinue
```

Si no existe:

```powershell
New-NetFirewallRule -Name 'CoCiber-SMB-Desde-A' -DisplayName 'CoCiber SMB desde Windows A' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 445 -RemoteAddress '10.10.30.10'
```

Si ya es la regla de este laboratorio, revisa su alcance con `Get-NetFirewallRule -Name 'CoCiber-SMB-Desde-A' | Get-NetFirewallAddressFilter`.

**Una regla acotada no anula otra regla más amplia.** Revisa las reglas entrantes activas de SMB antes de afirmar que solo A puede entrar. En B:

```powershell
Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq '445' } | Get-NetFirewallRule | Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' } | Select-Object Name,DisplayName,Profile
```

Para cada regla encontrada, consulta `Get-NetFirewallRule -Name 'NOMBRE_REAL' | Get-NetFirewallAddressFilter`. Si pertenece a esta VM de laboratorio y debe limitarse a A, el comando base es `Set-NetFirewallRule -Name 'NOMBRE_REAL' -RemoteAddress '10.10.30.10'`. Conserva registro del valor anterior. No modifiques una regla de dominio o de otro servicio sin revisar su uso. Reglas de puerto Any/programa o políticas de dominio también pueden permitir acceso: la prueba negativa desde Kali del paso 6 debe confirmar el resultado real.

## 6. Demostrar Kali → A → B

En la sesión SSH abierta en **A** como `ctf_win_demo`, dentro de PowerShell:

```powershell
Test-NetConnection -ComputerName 10.10.30.11 -Port 445
$nombreB = 'lab-winvict-b'
net use '\\10.10.30.11\COCIBER_DEMO' "/user:${nombreB}\ctf_smb_demo" * /persistent:no
Get-Content -LiteralPath '\\10.10.30.11\COCIBER_DEMO\evidencia.txt'
net use '\\10.10.30.11\COCIBER_DEMO' /delete
```

`net use` pide la contraseña privada de **B**. Debe aparecer `EVIDENCIA_WINDOWS_A_B`. Si falla la autenticación, revisa nombre de B, cuenta, contraseña, permisos y políticas; no actives acceso guest ni cambies UAC. Sal de PowerShell con `exit` y después de SSH con otro `exit` si la sesión abrió inicialmente cmd.

Desde una terminal **Kali**, comprueba que el acceso directo a B no está permitido si se aplicó el alcance solo-A:

```bash
nc -vz -w 3 10.10.30.11 445
```

Se espera fallo/timeout desde Kali y éxito desde A. Si Kali también entra, revisa las reglas amplias en B antes de aceptar el aislamiento. La demo acredita el recorrido de acceso autorizado; no demuestra ejecución remota de código ni una vulnerabilidad de Windows.

## 7. Cerrar la prueba y registrar

Cierra la conexión SMB y todas las sesiones SSH de prueba. En A y B, respectivamente, con PowerShell administrador:

```powershell
# Solo en A:
Disable-LocalUser -Name 'ctf_win_demo'
```

```powershell
# Solo en B:
Disable-LocalUser -Name 'ctf_smb_demo'
Get-SmbSession | Select-Object SessionId,ClientComputerName,ClientUserName
```

Deshabilitar una cuenta no desconecta una sesión SMB existente. Si todavía hay una sesión de esta práctica, cierra **solo su SessionId** con `Close-SmbSession -SessionId ID_VERIFICADO -Force`. Registra las reglas creadas y conserva el archivo hasta documentar el resultado. Para revertir completamente, utiliza el snapshot previo con las VM drenadas; no borres recursivamente carpetas con contenido no revisado.

Para repetir, el instructor puede habilitar estas mismas cuentas dedicadas con `Enable-LocalUser -Name 'NOMBRE_DE_CUENTA_DE_PRUEBA'` en su VM correspondiente. Son cuentas de ensayo manual, no cuentas por corrida. Continúa con [11. FTP](11_SRVFSAD_FTP.md) y [12. Integración pendiente](12_VALIDACION_WINDOWS_FTP.md).
