# 03. Verificar Guacamole y el acceso a Kali

**Antes:** plataforma accesible y módulo Guacamole actualizado según [02](02_ACTUALIZAR_INTERFAZ_Y_GUACAMOLE.md). Necesitas una cuenta de administrador del CTF. Todavía no necesitas crear laboratorios.

## 1. Consultar el inventario

En el navegador, entra a CoCiber con `admin_ctf`, abre **Guacamole** y pulsa **Actualizar inventario**. Debe aparecer «API verificada» con la hora. No crees conexiones duplicadas si aparece un error: revisa primero la configuración privada del capítulo anterior.

Busca LAB-KALI-BLUE y LAB-KALI-PURPLE. Revisa protocolo, IP y puerto. SSH utiliza normalmente 22; RDP, 3389. El puerto 2222 pertenece al ejercicio SSH de LNXVICT y no es el SSH administrativo de Kali.

## 2. Probar un puerto y, después, una sesión real

Pulsa **Probar puerto**. Un resultado correcto significa que la API alcanza ese puerto; no valida contraseña ni conectividad desde guacd. Verifica además que puedes iniciar sesión desde el portal Guacamole que ya administra el laboratorio.

Si no tienes una ruta web hacia Guacamole, el responsable puede autorizar este túnel temporal. Desde **PowerShell local**, deja abierta esta terminal:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:18080:10.10.10.10:8080 lab-rtrfw@10.195.20.20
```

Después abre `http://127.0.0.1:18080/guacamole/` en el navegador local. El túnel usa el puerto/contexto de la configuración existente; si tu Guacamole usa otros valores, consulta al responsable antes de sustituirlos. Entra con una cuenta **de Guacamole**, no con `admin_ctf` salvo que exista también allí. Ctrl+C cierra el túnel cuando termines. Si SSH rechaza forwarding, utiliza la ruta administrativa ya autorizada; no cambies el firewall ni SSH para saltar esa restricción.

## 3. Crear una conexión si realmente falta

En CoCiber → Guacamole → **Nueva conexión**:

1. Nombre descriptivo, por ejemplo `LAB-KALI-BLUE SSH`.
2. Selecciona la VM y el protocolo; no escribas otra IP a mano.
3. Usa la cuenta real de la VM proporcionada por su administrador.
4. Guarda y vuelve a comprobar el inventario.
5. Si utilizas una cuenta remota independiente, créala en **Cuenta remota** y asígnale la conexión mediante **Ver permisos**.

Estas conexiones son administrativas/permanentes. Las consolas de los jugadores se crean por corrida con cuentas temporales después de preparar los helpers; no usan automáticamente esta cuenta permanente.

## 4. Requisito especial para la demo web

La consola integrada de la instalación nueva es **SSH**, no un escritorio gráfico. Para hacer la demostración visual de DVWA necesitas un navegador ejecutado en Kali. Comprueba previamente una de estas vías:

- Escritorio RDP de Kali ya configurado y accesible en Guacamole con una cuenta de práctica autorizada.
- Consola gráfica de la Kali desde Nutanix, abierta por el administrador y con una cuenta de práctica.

Dentro del escritorio Kali, abre una terminal y ejecuta:

```bash
firefox http://10.10.30.20/dvwa/
```

Si no existe Firefox, usa el navegador instalado desde el menú de Kali. Si no hay escritorio o acceso autorizado, puedes preparar y demostrar ESC-02, pero **deja la demo visual ESC-03 pendiente**. No intentes abrir Firefox desde una consola SSH sin entorno gráfico ni desde Windows esperando alcanzar VLAN30.

Siguiente: [inventario y catálogo](04_INVENTARIO_Y_CATALOGO.md).

## Si una conexión RDP es rechazada

Continúa con [06. Router, Guacamole y escritorios RDP](06_DIAGNOSTICO_RDP_GUACAMOLE.md). No agregues DNAT de 3389: revisa primero el origen real de guacd, la interfaz elegida por LAB-GUAC y el servicio de la VM.
