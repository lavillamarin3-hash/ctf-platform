# 08. Caso confirmado: LAB-KALI-BLUE no abre RDP desde Guacamole Docker

Actualizado el **12 de noviembre de 2026**. Datos confirmados por el operador:

- LAB-GUAC: Ubuntu Server, `10.10.10.10`; Docker Compose con Guacamole **1.6.0**, guacd **1.6.0** y MariaDB **11.4**.
- El portal responde HTTP 200.
- Destino: LAB-KALI-BLUE, `10.10.20.12`; cuenta administrativa `lab-kali-blue`.
- Mensaje al abrir la conexión: «El servidor de escritorio remoto no está disponible actualmente».

El mensaje es genérico, pero las últimas salidas confirman un bloqueo en Kali: **Xfce está instalado, falta xorgxrdp, no existen las unidades xrdp/xrdp-sesman y no hay escucha en 3389 ni 3390.** Falta preparar el servicio RDP y después comprobar el recorrido desde guacd. No reinstales MariaDB ni reinicialices las conexiones para diagnosticarlo.

## Hallazgos de las salidas recibidas

| Comprobación | Evidencia | Conclusión |
| --- | --- | --- |
| Ruta del host a Kali | `via 10.10.10.1 dev ens3 src 10.10.10.10` | La selección de interfaz/origen es correcta; no aplicar cambios de rutas del paso 3 de la guía 06 |
| Ruta del host a Windows A | Mismo gateway, interfaz y origen | También correcta desde el host |
| TCP3389 hacia Kali | `Connection refused` | Rechazo activo; comprobar primero escucha/puerto de xrdp y firewall de Kali |
| Escritorio de Kali | `kali-desktop-xfce 2026.2.12` y `/usr/bin/startxfce4` | Xfce ya está instalado |
| Servidor RDP de Kali | Falta xorgxrdp, unidades xrdp/xrdp-sesman ausentes y ningún puerto escuchando | Instalar los paquetes RDP según la sección 2.1; el nombre `xrdp` sin versión en dpkg-query no acredita una instalación completa |
| TCP3389 hacia Windows A/B | Timeout | No hubo respuesta a tiempo; verificar RDP, firewall local y retorno por separado |
| Unidad guacd nativa | No existe | Esperado: este despliegue usa Docker |
| Contenedores | Web activo; guacd y MariaDB activos y healthy | Los procesos están funcionando; no acredita una sesión RDP completa |
| Red Docker | `docker0` DOWN y puentes personalizados UP | No demuestra un fallo: Compose puede utilizar los puentes personalizados |

La cuenta de mantenimiento confirmada de LAB-GUAC es **`labadmin`**. Contenedores: `guacamole-guacamole-1`, `guacamole-guacd-1` y `guacamole-db-1`.

**Siguiente paso: ejecutar la sección 2.1 en Kali.** La ausencia de escucha ya está confirmada. Después se debe repetir la prueba desde LAB-GUAC y desde el espacio de red de guacd; todavía no se ha validado una sesión completa. Las reglas compartidas ya permiten VLAN 10 hacia VLAN 20: este hallazgo no requiere abrir otro puerto en el router.

## 1. Distinguir los tres tramos

```text
Equipo 10.195.20.x → portal Guacamole → contenedor guacd → Kali 10.10.20.12:3389
                    HTTP/HTTPS        TCP4822 interno    RDP
```

Si accedes con el navegador al portal, el origen RDP es guacd, no tu equipo de gestión. Si intentas usar directamente `mstsc` contra `10.10.20.12`, es otro recorrido: las reglas actuales no autorizan ese acceso directo. Esta guía resuelve el acceso **mediante Guacamole**.

Guacamole web y guacd son componentes separados. En una instalación Docker típica se comunican por una red Docker, sin publicar TCP4822 en gestión. [Arquitectura Docker de Guacamole 1.6.0](https://guacamole.apache.org/doc/1.6.0/gug/guacamole-docker.html).

## 2. Primero: comprobar RDP en LAB-KALI-BLUE

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-kali-blue@10.10.20.12
```

Introduce las contraseñas cuando SSH las solicite. En la terminal de Kali:

```bash
hostname
ip -br address
ip route get 10.10.10.10
command -v startxfce4
dpkg-query -W xrdp xorgxrdp kali-desktop-xfce
sudo systemctl status xrdp xrdp-sesman --no-pager
sudo ss -lntp '( sport = :3389 or sport = :3390 )'
```

Resultados esperados: `lab-kali-blue`, IP `.20.12`, retorno por `10.10.20.1`, escritorio instalado y xrdp escuchando en **3389** sobre una dirección accesible, no solo `127.0.0.1`.

- Si no existe xrdp/escritorio, aplica el paso 6 de [06. Diagnóstico RDP](06_DIAGNOSTICO_RDP_GUACAMOLE.md#6-preparar-kali-para-una-práctica-gráfica).
- Si están instalados pero detenidos, y no hay otra sesión gráfica en uso, ejecuta `sudo systemctl start xrdp` y repite las comprobaciones. Si falla, consulta sus registros; no lo reinicies repetidamente.
- Si escucha en **3390**, la conexión configurada en 3389 no funcionará. Revisa el puerto real en la sección `[Globals]` de `/etc/xrdp/xrdp.ini`. CoCiber actualmente admite RDP3389: acuerda el cambio del servicio a 3389 fuera de sesiones activas, o prueba el puerto real desde la administración nativa de Guacamole sin modificar la lista de puertos de CoCiber a ciegas.

Para revisar configuración y registros, sin mostrar claves privadas:

```bash
sudo grep -nE '^\[|^port=|^security_layer=|^certificate=|^key_file=' /etc/xrdp/xrdp.ini
sudo journalctl -u xrdp -u xrdp-sesman --since '10 minutes ago' --no-pager
```

Las otras secciones de xrdp pueden contener parámetros `port` para sus sesiones; no hagas una sustitución global de todos ellos.

### 2.1. Corregir la instalación RDP ausente en Kali

Ejecuta estos comandos **en LAB-KALI-BLUE**, conectado como `lab-kali-blue`. Xfce ya existe: basta con instalar el servidor RDP y su integración con Xorg. Esta combinación está documentada por [Kali: Xfce con RDP](https://www.kali.org/docs/general-use/xfce-with-rdp/).

Primero actualiza el índice de paquetes:

```bash
sudo apt-get update
```

Si hay errores de DNS, repositorios o descarga, detente y conserva la salida. Solo después de actualizar correctamente, instala:

```bash
sudo apt-get install xrdp xorgxrdp
```

Acepta la instalación cuando se solicite. Si termina correctamente, habilita el servicio:

```bash
sudo systemctl enable --now xrdp
```

Comprueba el resultado:

```bash
dpkg-query -W -f='${binary:Package}\t${db:Status-Abbrev}\t${Version}\n' xrdp xorgxrdp
sudo systemctl status xrdp xrdp-sesman --no-pager
sudo ss -lntp '( sport = :3389 or sport = :3390 )'
```

Espera paquetes con estado `ii`, servicios `active (running)` y escucha en **3389** accesible desde la red. Si aparece otro puerto, sigue la revisión de `[Globals]` de la sección 2. Si falla el arranque, recoge el error antes de continuar:

```bash
sudo journalctl -u xrdp -u xrdp-sesman -n 80 --no-pager
```

Una vez que exista escucha, continúa con las secciones 3 y 4 **en LAB-GUAC**. El éxito de la instalación no confirma todavía autenticación, certificados ni apertura del escritorio. Para la primera prueba usa la conexión administrativa de la sección 7 y selecciona Xorg si xrdp presenta un selector de sesión.

## 3. Identificar los contenedores en LAB-GUAC

Abre otra terminal y entra a **LAB-GUAC** con su cuenta Linux administrativa habitual. Si necesitas conectarte desde PowerShell:

```powershell
ssh -J lab-rtrfw@10.195.20.20 labadmin@10.10.10.10
```

Ya en LAB-GUAC, ejecuta:

```bash
hostname
sudo docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
guac_web=guacamole-guacamole-1
guacd_container=guacamole-guacd-1
sudo docker inspect --format '{{.Name}} {{.Config.Image}} estado={{.State.Status}} red={{.HostConfig.NetworkMode}} {{range $name,$net := .NetworkSettings.Networks}}{{$name}}={{$net.IPAddress}} {{end}}' "$guac_web" "$guacd_container"
```

Los nombres anteriores están confirmados en las salidas recibidas. Si el despliegue se recreó con otro nombre, actualízalos según `docker ps`. Ambos deben estar en ejecución. En la modalidad bridge habitual deben compartir una red Docker que permita su comunicación; si usan una arquitectura distinta, registra esa diferencia.

Consulta solo las variables de conexión a guacd, sin imprimir contraseñas de BD:

```bash
sudo docker exec "$guac_web" sh -c 'printf "GUACD_HOSTNAME=%s\nGUACD_PORT=%s\nGUACD_SSL=%s\n" "$GUACD_HOSTNAME" "${GUACD_PORT:-4822}" "${GUACD_SSL:-false}"'
```

`GUACD_HOSTNAME` debe resolver al servicio guacd real. `localhost` apunta al contenedor web en una instalación bridge normal y no a otro contenedor. Un hostname vacío no prueba por sí solo un fallo: puede haber configuración montada o un valor por defecto; contrástalo con el Compose real. TLS de Guacamole hacia guacd es independiente de TLS de RDP hacia Kali.

## 4. Probar guacd → LAB-KALI-BLUE

En la misma sesión de LAB-GUAC:

```bash
ip route get 10.10.20.12
command -v nc
command -v nsenter
nc -vz -w 3 10.10.20.12 3389
guacd_pid=$(sudo docker inspect --format '{{.State.Pid}}' "$guacd_container")
if [ "$guacd_pid" -gt 0 ] 2>/dev/null; then
  sudo nsenter -t "$guacd_pid" -n ip route get 10.10.20.12
  sudo nsenter -t "$guacd_pid" -n nc -vz -w 3 10.10.20.12 3389
else
  echo 'guacd no está en ejecución; revisar sus registros.'
fi
```

Si falta `nc`, instala `netcat-openbsd` en LAB-GUAC desde su repositorio autorizado. `nsenter` pertenece a `util-linux`. Se usan las herramientas del host dentro del espacio de red de guacd: no hace falta instalar paquetes dentro del contenedor.

| Host LAB-GUAC | Espacio de red guacd | Interpretación |
| --- | --- | --- |
| Falla | Falla | Revisar escucha en Kali, ruta, retorno y firewall |
| Correcto | Falla | Revisar red Docker, reenvío/NAT del host y salida del contenedor |
| Correcto | Correcto | TCP3389 funciona; continuar con conexión interna, registros y parámetros RDP |

Las reglas del router permiten VLAN10→VLAN20 si el origen observado pertenece a `10.10.10.0/24`. El origen dentro de Docker puede ser privado y cambiar por NAT al salir. Si LAB-GUAC elige su interfaz de gestión, aplica el diagnóstico de rutas del paso 3 de la guía 06. No agregues una regla amplia de gestión→Kali para ocultar una ruta incorrecta.

## 5. Si hay dudas sobre Guacamole → guacd

Si el intento no aparece en los registros de guacd, revisa primero los del contenedor web (paso 6). Para comprobar TCP dentro de la red Docker, toma de `docker inspect` la **IP de guacd en la red compartida** y el puerto configurado:

```bash
read -rp 'IP de guacd en la red Docker compartida, obtenida de inspect: ' guacd_ip
read -rp 'Puerto interno de guacd comprobado (habitualmente 4822): ' guacd_port
guac_web_pid=$(sudo docker inspect --format '{{.State.Pid}}' "$guac_web")
if [ "$guac_web_pid" -gt 0 ] 2>/dev/null; then
  sudo nsenter -t "$guac_web_pid" -n nc -vz -w 3 "$guacd_ip" "$guacd_port"
else
  echo 'La aplicación Guacamole no está en ejecución.'
fi
```

Esto comprueba TCP por IP, no resolución DNS ni TLS. Si la IP responde y el hostname configurado no, revisa los alias de servicio en la red Docker. No cambies el Compose a una IP efímera como solución permanente. No necesitas publicar 4822 ni 3389 en el host Docker para estos flujos de salida.

## 6. Reproducir una vez y leer ambos registros

En el navegador abre **la conexión RDP de LAB-KALI-BLUE** una sola vez. Inmediatamente después, en LAB-GUAC:

```bash
date -Is
sudo docker logs --since 5m --tail 100 "$guac_web"
sudo docker logs --since 5m --tail 100 "$guacd_container"
```

Y en la terminal de Kali:

```bash
sudo journalctl -u xrdp -u xrdp-sesman --since '5 minutes ago' --no-pager
sudo tail -n 60 /var/log/xrdp.log /var/log/xrdp-sesman.log
```

Si no hay entradas de xrdp, aún puede haber un fallo anterior a la sesión o un rechazo TLS; correlaciona con guacd. Si faltan los archivos de log, conserva el mensaje y la salida del journal. [Diagnóstico mediante registros de Guacamole 1.6.0](https://guacamole.apache.org/doc/1.6.0/gug/troubleshooting.html).

## 7. Parámetros de la conexión y siguiente corrección

Para esta prueba administrativa, en Guacamole:

| Campo | Valor |
| --- | --- |
| Protocolo | RDP |
| Hostname | 10.10.20.12 |
| Puerto | 3389, si coincide con la escucha comprobada |
| Usuario | lab-kali-blue |
| Contraseña | La contraseña Linux de esa cuenta, introducida en privado |
| Dominio | Vacío |
| Modo de seguridad | Compatible con xrdp; no forzar NLA de Windows |

Si el error es de certificado, atiende identidad/confianza TLS; no actives «ignorar certificado» como cambio general. Si los registros indican falta de lectura de la clave TLS de xrdp, revisa **la ruta y los permisos de ese archivo concreto** antes de modificar grupos; no hagas `chmod 777` ni compartas su contenido. Si autentica pero el escritorio se cierra, revisa Xfce/Xorg y conflictos con una sesión gráfica local.

La cuenta administrativa se usa únicamente para comprobar el servicio. No entregues esa conexión a los jugadores. La asignación automática fresh sigue siendo SSH y no cambia de protocolo por instalar xrdp.

## 8. Evidencia necesaria para cerrar el diagnóstico

Conserva las salidas de escucha/servicios de Kali, ruta del host, resultado TCP desde guacd y mensajes coincidentes de ambos contenedores. Oculta contraseñas, tokens y contenido ajeno al ensayo antes de compartirlos. Con esos datos se podrá aplicar una corrección concreta; el HTTP 200 y el mensaje genérico aún no permiten escogerla.
