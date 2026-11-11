# 09. Preparar Windows y FTP: orden de ejecución

Confirmado por el operador el **10 de noviembre de 2026**: ya se puede iniciar un reto y abrir la sesión SSH de la Kali atacante. Windows A y B usan **Windows 10 Pro**; LAB-SRVFSAD usa **Ubuntu Server 26.04**.

| Orden | Documento | Equipo y resultado |
| --- | --- | --- |
| 1 | Este documento | Revisar alcance, cuentas y snapshots |
| 2 | [10. Windows A y B](10_WINDOWS_A_Y_B.md) | SSH en A y lectura SMB de un archivo de prueba de B desde A |
| 3 | [11. Servidor FTP](11_SRVFSAD_FTP.md) | Descargar un archivo de prueba desde la Kali por FTP pasivo |
| 4 | [12. Validación e integración](12_VALIDACION_WINDOWS_FTP.md) | Registrar pruebas y las condiciones para conectar estos servicios a corridas |

## 1. Alcance de estas guías

Se configuran servicios reales y cuentas locales de práctica para comprobar los recorridos **Kali → Windows A → Windows B** y **Kali → servidor FTP**. Incluyen una demostración manual y su limpieza. No contienen contraseñas administrativas ni modifican la BD del CTF.

**Preparar el servicio no habilita automáticamente ESC-04/05 en CoCiber.** El código actual no implementa la reserva simultánea de las dos Windows ni un adaptador FTP. Mantén esos retos en borrador y las VM nuevas fuera de la asignación automática. Los archivos `EVIDENCIA_*` de estas guías son pruebas de infraestructura, no banderas aceptadas por la plataforma. La integración pendiente está delimitada en [12](12_VALIDACION_WINDOWS_FTP.md).

El catálogo anterior definía ESC-05 por Samba. La nueva petición es **FTP**: no conviertas el reto existente cambiando únicamente su descripción ni actives `EXFIL-SMB-LAB` pensando que usará FTP. Estas guías sustituyen la preparación Samba de SRVFSAD para la nueva demo; Windows continúa usando SMB para A→B.

## 2. Comprobar las VM

| VM | IP | Cuenta de mantenimiento confirmada | Función en esta fase |
| --- | --- | --- | --- |
| LAB-WINVICT-A | 10.10.30.10 | `lab-winvict-a` | Entrada SSH y cliente SMB hacia B |
| LAB-WINVICT-B | 10.10.30.11 | `lab-winvict-b` | Recurso SMB de lectura |
| LAB-SRVFSAD | 10.10.30.21 | `lab-srvfsad` | FTP pasivo de lectura |
| LAB-KALI-BLUE / PURPLE | 10.10.20.12 / 10.10.20.11 | `lab-kali-blue` / `lab-kali-purple` | Clientes ya preparados |

Accede inicialmente a Windows mediante **la consola de Nutanix**, con `lab-winvict-a\lab-winvict-a` en A y `lab-winvict-b\lab-winvict-b` en B. Los nombres de equipo confirmados son `lab-winvict-a` y `lab-winvict-b`. Usa la contraseña facilitada por el responsable cuando Windows la solicite; no queda almacenada en el repositorio. Comprueba la elevación administrativa en la guía 10. No se asume SSH instalado. En Ubuntu se conserva la cuenta administrativa `lab-srvfsad`.

Antes de modificar, confirma que no hay corridas ni usuarios trabajando en esas VM y solicita snapshots de A, B y SRVFSAD. Registra nombre real y fecha de cada snapshot. Las guías de instalación de servicios necesitan acceso a Windows Update o al repositorio Ubuntu autorizado; si no lo tienen, solicita paquetes/capacidades de la misma versión. No cambies el router para dar Internet permanente.

## 3. Cuentas y sesiones

Se crearán tres cuentas **de prueba**, con contraseñas privadas nuevas: `ctf_win_demo` en A, `ctf_smb_demo` en B y `ctf_ftp_demo` en SRVFSAD. No uses las contraseñas de mantenimiento, del administrador CTF ni de las BD. No agregues estas cuentas a Administradores o sudo.

Las cuentas son temporales para un ensayo supervisado de un participante. La futura integración deberá crear cuentas y evidencias separadas por corrida. Si necesitas varias prácticas simultáneas, espera esa integración antes de habilitarlas.

Puedes ejecutar las comprobaciones desde una Kali administrativa o desde la sesión de jugador ya funcional, si el instructor incluye estas tres IP como destinos autorizados de su ensayo. No alteres un reto publicado para representar un escenario que el backend todavía no soporta.

## 4. Ubicación del proyecto web

La ruta nominal de las guías era `/ctf-plataform/`, pero el servidor fue verificado en **`/home/lab-ctfweb/ctf-platform`**. Para cualquier comando posterior de plataforma, entra como `lab-ctfweb`, ejecuta `cd ~/ctf-platform` y confirma con `pwd -P`, `test -f .env.fresh` y `test -f deploy/docker-compose.fresh.yml`. Conserva el ajuste local de WorkingDirectory ya aplicado al worker. No muevas el despliegue para ejecutar estas guías.
