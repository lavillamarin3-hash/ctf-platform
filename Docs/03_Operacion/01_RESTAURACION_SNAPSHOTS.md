# 01. Restaurar una víctima y volver a habilitarla

**Cuándo:** después de una corrida real DVWA que dejó la VM en «Requiere restauración», o durante mantenimiento planificado. Requiere acceso de administrador a CoCiber, un snapshot conocido y al encargado de Nutanix. La plataforma no restaura snapshots automáticamente.

## 1. Dejar de asignar la máquina

En **Máquinas**, pulsa **Drenar** si estaba disponible. Si ya está «Requiere restauración» o «En mantenimiento», conserva ese estado. En **Corridas**, revisa las sesiones afectadas. Pide a cada jugador pulsar **Cerrar corrida** dentro de su reto; la tabla administrativa de Corridas es de consulta y no tiene ese botón.

Espera hasta que todas las corridas de esa VM estén **Liberadas**. «Limpiando» (`reiniciando`) significa que la limpieza sigue pendiente. Si no termina, revisa el worker y la conectividad antes de restaurar. No elimines filas de reservas ni fuerces el estado de la máquina.

## 2. Registrar y restaurar en Nutanix

Anota VM/IP, motivo, responsable y nombre exacto del snapshot que se utilizará. El encargado debe comprobar de nuevo que no quedan sesiones vivas y restaurar **esa víctima** desde Prism, siguiendo el procedimiento de la versión instalada. No selecciones un snapshot de la plataforma o de la BD para resolver una práctica DVWA.

Un snapshot de la víctima no revierte reservas, puntuaciones ni cuentas Guacamole, que están fuera de ella. Por eso se cierra y limpia primero en CoCiber.

## 3. Comprobar el estado restaurado

Desde PowerShell local, entra a la víctima. Ejemplo para LAB-SRVWEB:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
```

En la víctima:

```bash
hostname
ip -brief address
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
sudo stat -c '%U:%G %a %n' /usr/local/sbin/ctf-dvwa-lab
sudo python3 -m py_compile /usr/local/sbin/ctf-dvwa-lab
sudo -u labops sudo -n -l
```

Para LNXVICT usa su [acceso y comprobaciones](../02_Laboratorios/03_LNXVICT_SSH.md). Una restauración puede revertir scripts, permisos, claves o la tabla de DVWA. Si falta algo, repite únicamente la preparación correspondiente. Si cambió una huella SSH, verifícala con el encargado y actualiza known_hosts mediante la [guía de claves](../02_Laboratorios/02_CUENTA_TECNICA_Y_CLAVES.md); no desactives su comprobación.

## 4. Probar desde LAB-CTFWEB

Abre otra ventana PowerShell:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

En LAB-CTFWEB:

```bash
cd /ctf-plataform/ || exit 1
sudo systemctl status cociber-fresh-worker.service --no-pager
sudo bash scripts/probar_inyector.sh LAB-SRVWEB DVWA-SQLI-LAB
```

Para LNXVICT, sustituye **solo el último comando** por:

```bash
sudo bash scripts/probar_inyector.sh LAB-LNXVICT SSH-PASSWORD-LAB
```

Esperado: `create → check → destroy: OK`. La ficha permanece en mantenimiento. Si hay error, corrígelo y vuelve a probar; no habilites la víctima todavía.

## 5. Confirmar desde la plataforma

Como administrador, abre **Mantenimiento**. En el registro pendiente de esa víctima pulsa **Confirmar restauración probada**. El botón exige una prueba correcta y la API comprueba que no existan corridas vivas. Después verifica en **Máquinas** que esté disponible.

Si era un mantenimiento planificado sin registro de restauración pendiente, confirma **Disponible** en Máquinas solamente después de completar y registrar las comprobaciones anteriores. Para el caso DVWA dirty, utiliza siempre su registro de Mantenimiento.

Windows A→B sigue pendiente: no utilices este procedimiento para habilitar ESC-04 mientras falten sus helpers y la coordinación de ambas VM.

Para mantenimiento general consulta [02. Respaldos y actualizaciones](02_RESPALDOS_Y_ACTUALIZACIONES.md).
