# ESC-04: guía para documentar Windows A→B

**Estado:** `LATERAL-SMB-LAB`, T1021.002, avanzado, 500 puntos, **deshabilitado**. La cadena confirmada es LAB-WINVICT-A (10.10.30.10) → LAB-WINVICT-B (10.10.30.11). No se sustituirá por LAB-LNXVICT.

## 1. Registrar acceso y snapshots

Accede a cada Windows mediante su consola Nutanix o el mecanismo administrativo ya autorizado. No se presupone que Windows tenga SSH. Registra nombre, IP, forma de acceso y snapshot previo de A y B. No se restauran snapshots durante el diagnóstico.

## 2. Recopilar datos básicos en PowerShell

En **cada VM**, con permisos administrativos para las consultas que lo requieran:

```powershell
hostname
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, CsDomain, CsPartOfDomain
Get-NetIPConfiguration
Get-Service -Name WinRM,LanmanServer | Select-Object Name,Status,StartType
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 445,5985,5986 | Select-Object LocalAddress,LocalPort,OwningProcess
winrm enumerate winrm/config/listener
Get-ChildItem Cert:\LocalMachine\My | Select-Object Subject,Thumbprint,NotAfter,HasPrivateKey
```

Comparte metadatos de los certificados, **nunca** exportaciones PFX, claves privadas o contraseñas. No ejecutes `Enable-PSRemoting`, no agregues TrustedHosts y no desactives la validación TLS para obtener un resultado positivo.

## 3. Documentar cuenta técnica y helper

Entrega el **nombre** de la cuenta prevista, si es local o de dominio, grupos/permisos y en cuál VM existe. La contraseña se instalará después como secreto privado; no se incluye en este documento.

Consulta cuentas locales y recursos, sin contraseñas:

```powershell
Get-LocalUser | Select-Object Name,Enabled
Get-SmbShare | Select-Object Name,Path,Description
```

Con el nombre real del recurso elegido:

```powershell
$recursoCTF = Read-Host 'Nombre del recurso de práctica existente'
Get-SmbShareAccess -Name $recursoCTF
```

Si existe un script de laboratorio, entrega ruta, propietario, ACL, acciones admitidas y código revisado sin secretos. Si no existe, anota **«helper pendiente de implementar»**. No inventar una ruta PowerShell para habilitar el adaptador.

## 4. Definir la técnica y el alcance de A→B

Completa esta ficha con el instructor:

| Campo | Decisión necesaria |
| --- | --- |
| Punto de entrada | Qué acceso de práctica recibe el jugador en A |
| Movimiento lateral | Servicio SMB concreto y acción didáctica permitida |
| Credenciales de práctica | Método de generación/entrega; solo nombre de cuenta en la ficha |
| Recurso en B | Recurso y ruta donde se coloca la evidencia por corrida |
| Cambios en A | Cuentas, permisos o archivos temporales |
| Cambios en B | Cuentas, permisos o archivos temporales |
| Limpieza | Cómo se confirma la eliminación en ambas máquinas |
| Restauración | Snapshot a usar y responsable de confirmar A y B |

Desde A, una comprobación de conectividad limitada al destino autorizado es:

```powershell
Test-NetConnection -ComputerName 10.10.30.11 -Port 445
```

Registra el resultado. Esta consulta no comprueba permisos SMB ni demuestra movimiento lateral: ambas validaciones pertenecen a la siguiente fase.

## 5. Preparar WinRM sin debilitarlo

Registrar URL HTTPS/puerto real, nombre certificado, CA utilizada y forma de validarla desde LAB-CTFWEB. Si solo hay HTTP/5985 o no hay certificado válido, déjalo como hallazgo pendiente, no como autorización para ignorar certificados.

El contrato futuro debe transportar la flag por **stdin**. Pasarla en `run_ps`, un comando codificado o argumentos de PowerShell no cumple este requisito. Se debe probar el transporte de entrada y el helper antes de conectar `WinRmInjector` a corridas reales.

## 6. Pendiente de arquitectura específico

La versión actual reserva **una víctima** por corrida. Antes de habilitar A→B hay que reservar las **dos** máquinas atómicamente y mantener ambas bloqueadas hasta terminar su limpieza. No basta con seleccionar A como víctima y escribir B en una descripción.

El caso de prueba obligatorio fuerza un fallo después de preparar A y antes de terminar B: ambos recursos deben compensarse y ninguna de las dos VM puede entregarse a otra corrida mientras la limpieza esté pendiente.

## 7. Entrega para la siguiente fase

Envía fichas de A/B, metadatos WinRM/certificados, nombre de cuenta técnica, definición de la técnica SMB, helper existente o pendiente y snapshots. Con esos datos se implementarán el adaptador real, las reservas de dos víctimas y el piloto. `WINRM_INJECTOR_ENABLED` permanecerá false hasta entonces.
