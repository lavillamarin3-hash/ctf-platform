# Demo vulnerable aislada: SSH y web

Paquete local para la demostración técnica de CoCiber. Crea dos servicios deliberadamente inseguros y solo debe ejecutarse dentro de las VLAN del laboratorio:

| Escenario | Host | Origen permitido | Servicio |
| --- | --- | --- | --- |
| Credenciales SSH | LAB-LNXVICT 10.10.30.12 | LAB-KALI-BLUE 10.10.20.12 | 22222/TCP |
| Portal web SQL vulnerable | LAB-SRVWEB 10.10.30.20 | LAB-KALI-PURPLE 10.10.20.11 | 8088/TCP |

Los servicios usan network_mode: host para ver la IP real de la Kali y rechazar cualquier otro origen. No incluyen privilegios, volúmenes del host, acceso a la plataforma, ni datos reales. No los expongas mediante DNAT, Internet, Guacamole hacia la víctima ni una interfaz de gestión.

## 1. Preparar secretos de demostración

En una estación de operación, genera dos banderas y un secreto de sesión. Mantén los valores fuera de Git, terminal compartida y capturas. En cada VM, copia este directorio a una ruta local, por ejemplo /opt/cociber-demo, y crea un .env privado a partir de .env.example.

Los valores de DEMO_SSH_FLAG y DEMO_WEB_FLAG deben conservarse temporalmente: se solicitarán de forma oculta al crear los retos estáticos en la plataforma. Los usuarios de servicio son independientes de las cuentas de administración de las VMs.

| Cuenta | Ubicación | Uso |
| --- | --- | --- |
| DEMO_SSH_USERNAME | Archivo .env de LNXVICT | Usuario débil del servicio SSH de práctica. |
| DEMO_WEB_STUDENT_USER | Archivo .env de SRVWEB | Cuenta normal del portal vulnerable. |
| Jugador de CoCiber | Administración → Usuarios | Cuenta de prueba añadida al grupo CTF-DEMO-2026. |

Las dos primeras son cuentas sintéticas del laboratorio. Elige contraseñas solo para la demostración y no reutilices cuentas ni contraseñas de las VMs.

## 2. Iniciar el servicio SSH en LNXVICT

En LAB-LNXVICT, sin corridas activas del piloto:

~~~bash
cd /opt/cociber-demo
sudo docker compose --env-file .env -f compose.yml --profile lnxvict config --quiet
sudo docker compose --env-file .env -f compose.yml --profile lnxvict up -d --build ssh-demo
sudo docker compose --env-file .env -f compose.yml logs --tail=30 ssh-demo
~~~

El registro debe indicar que escucha en 10.10.30.12:22222 y que solo acepta 10.10.20.12. Desde Kali Blue comprueba únicamente la conectividad al puerto del reto. El SSH administrativo en 22 queda fuera del alcance.

## 3. Iniciar el portal web en SRVWEB

En LAB-SRVWEB:

~~~bash
cd /opt/cociber-demo
sudo docker compose --env-file .env -f compose.yml --profile srvweb config --quiet
sudo docker compose --env-file .env -f compose.yml --profile srvweb up -d --build web-demo
sudo docker compose --env-file .env -f compose.yml logs --tail=30 web-demo
~~~

Desde Kali Purple, prueba salud y acceso solo al portal asignado:

~~~bash
curl --fail http://10.10.30.20:8088/health
~~~

El portal contiene una consulta SQL concatenada intencionalmente vulnerable. Su base SQLite vive únicamente en el volumen local del contenedor. No conecta con MariaDB, DVWA ni PostgreSQL de CoCiber.

## 4. Crear los retos de la plataforma

Antes de continuar, en CoCiber confirma que están ready tanto las VMs como sus laboratorios: LNXVICT, SRVWEB, Kali Blue y Kali Purple. En Guacamole debe existir una conexión SSH o RDP funcional para cada Kali, y el jugador piloto debe tener permiso READ.

Ejecuta primero el ensayo desde LAB-CTFWEB:

~~~bash
sudo docker compose -f docker-compose.prod.yml \
  -f deploy/docker-compose.ssh-lab-secrets.yml \
  exec -T api python configure_demo_vulnerable_catalog.py \
  --group CTF-DEMO-2026
~~~

El ensayo no crea datos. Para aplicar, abre una TTY: las dos banderas se piden sin eco y deben coincidir exactamente con DEMO_SSH_FLAG y DEMO_WEB_FLAG.

~~~bash
sudo docker compose -f docker-compose.prod.yml \
  -f deploy/docker-compose.ssh-lab-secrets.yml \
  exec api python configure_demo_vulnerable_catalog.py \
  --group CTF-DEMO-2026 --apply
~~~

El configurador crea en borrador y asigna al grupo:

- DEMO-SSH-CONTAINER, que abre Kali Blue y apunta a LNXVICT :22222.
- DEMO-WEB-SQLI, que abre Kali Purple y apunta a SRVWEB :8088.

Publica ambos retos manualmente solo después de validar los servicios. Crea un usuario jugador de prueba desde Administración → Usuarios y agrégalo a CTF-DEMO-2026; no guardes su contraseña en este repositorio.

## 5. Finalizar la demostración

Primero cierra las corridas de los jugadores. En cada VM, detén solo su perfil:

~~~bash
sudo docker compose --env-file .env -f compose.yml --profile lnxvict stop ssh-demo
sudo docker compose --env-file .env -f compose.yml --profile srvweb stop web-demo
~~~

No uses down -v durante una demostración. Si se necesita reiniciar el contenido de la práctica, agenda una ventana y elimina únicamente el volumen local del perfil afectado tras confirmar que no hay corridas ni evidencia que conservar.

