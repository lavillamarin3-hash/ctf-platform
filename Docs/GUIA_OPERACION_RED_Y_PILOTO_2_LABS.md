# Operación por VLAN y piloto de dos laboratorios

Esta guía corresponde a la red AHV del proyecto. No expone contraseñas, flags,
claves privadas ni servicios del laboratorio a Internet.

## Topología confirmada

| Segmento | Red | Servicios relevantes |
| --- | --- | --- |
| Gestión Nutanix | `10.195.20.0/24` | Equipo del operador, Prism y salto SSH `LAB-RTRFW` (`10.195.20.20`) |
| Administración | `10.10.10.0/24` | CTFWEB `.13`, PostgreSQL/Redis `.14`, Guacamole `.10` |
| Atacantes | `10.10.20.0/24` | `LAB-KALI-PURPLE` `.11`, `LAB-KALI-BLUE` `.12` |
| Víctimas | `10.10.30.0/24` | `LAB-LNXVICT` `.12`, `LAB-SRVWEB` `.20` |

`LAB-RTRFW` es el único salto de administración entre gestión y las VLAN. La
API CTF llega desde VLAN 10 a las víctimas; los alumnos llegan desde las Kali
en VLAN 20. El acceso de mantenimiento se realiza con `ProxyJump`, por ejemplo:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
```

El segundo salto se origina en el router; por ello las víctimas ven al router,
no al equipo local. No añadir rutas directas desde gestión a VLAN 20/30.

## Mapeo aplicado en la plataforma

| Reto | Atacante | Víctima | Servicio permitido |
| --- | --- | --- | --- |
| `ESC-02-BRUTEFORCE` | `LAB-KALI-BLUE` (`10.10.20.12`) | `LAB-LNXVICT` (`10.10.30.12`) | SSH didáctico `2222` |
| `ESC-03-WEBEXPLOIT` | `LAB-KALI-PURPLE` (`10.10.20.11`) | `LAB-SRVWEB` (`10.10.30.20`) | DVWA HTTP `80` |

La plataforma exige exactamente una Kali reconocida en las referencias del
reto. La terminal Guacamole se resuelve por la IP fija de esa Kali y requiere
el permiso `READ` del alumno. No se entrega una conexión Guacamole a la
víctima.

## Antes de desplegar

1. Reserve una ventana sin corridas activas y confirme un respaldo recuperable
   de PostgreSQL.
2. Desde `LAB-CTFWEB`, confirme que el checkout está limpio y que API/web,
   PostgreSQL y Redis responden. No copie `.env.example` encima del `.env`
   privado.
3. En el `.env` privado de CTFWEB, indique las rutas locales de las claves
   dedicadas y de sus `known_hosts` mediante las cuatro variables `*_HOST`.
   Conserve las rutas internas `/run/secrets/...` y deje ambos laboratorios
   deshabilitados hasta completar las verificaciones.
4. En Guacamole, registre una conexión SSH o RDP única para cada Kali (`.11`
   y `.12`), y valide una sesión real con una cuenta de prueba.
5. En el inventario CTF, registre las cuatro VM con el nombre, IP y estado
   `ready` exactos. No continúe si una IP está duplicada.
6. Antes de publicar, compruebe el destino real del DNAT HTTPS. La regla del
   router que traduce `CTF_PUB:443` a `10.10.10.13:443` solo es válida si un
   proxy TLS escucha realmente en el puerto 443 de CTFWEB. Si Docker expone el
   frontend en 80, el proxy o la regla DNAT deben coincidir; no abrir un puerto
   adicional como solución temporal.

## Despliegue de plataforma

En `LAB-CTFWEB`, desde el checkout de producción y con el `.env` existente:

```bash
git pull --ff-only origin main
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml config --quiet
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml build api web
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml run --rm --no-deps api python -m app.check_services
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml up -d --force-recreate --wait api web
sudo docker compose -f docker-compose.prod.yml -f deploy/docker-compose.ssh-lab-secrets.yml exec -T api python -m app.check_services --http
```

No usar `down -v`, `FLUSHDB`, restauraciones SQL ni credenciales de ejemplo.

## Piloto 1: fuerza bruta didáctica

El backend instala al iniciar la corrida el servicio Paramiko restringido en
LNXVICT. Se enlaza en `10.10.30.12:2222` y acepta solamente tráfico de
`10.10.20.12`. OpenSSH administrativo de puerto 22 no forma parte del reto.

1. Ejecute primero `configure_vm_catalog.py` sin `--apply` y revise el cambio;
   aplíquelo solo si `ESC-02` está inactivo y sus referencias pasan a
   `LAB-KALI-BLUE` y `LAB-LNXVICT`.
2. Asigne el reto a un grupo piloto y sincronice sus permisos de Guacamole.
3. Inicie una sola corrida. Desde Blue use únicamente el diccionario de doce
   candidatos y el comando mostrado por la plataforma contra `:2222`.
4. Valide una flag, cierre la corrida, confirme que el acceso temporal ya no
   sirve y abra una segunda corrida para verificar una flag distinta.

## Piloto 2: DVWA

Antes de activar `DVWA_LAB_ENABLED=true`, en SRVWEB confirme Apache, MariaDB,
la ruta `/dvwa/`, la base `ctf_app_db.secrets`, y el helper restringido
`/usr/local/sbin/ctf-dvwa-flag`. `labops` debe usar exclusivamente una clave
SSH conocida desde el contenedor API; la clave y `known_hosts` se montan de
solo lectura y no se guardan en Git.

Al habilitar este segundo laboratorio, añada también
`-f deploy/docker-compose.dvwa-lab-secrets.yml` a **todos** los comandos
Compose anteriores. Así la API recibe los cuatro archivos privados; no monte
la clave de DVWA mientras el piloto SSH sea el único laboratorio activo.

1. Ejecute `configure_dvwa_catalog.py --group CODIGO` sin `--apply`. El reto
   debe quedar con `LAB-KALI-PURPLE` y `LAB-SRVWEB` y sin publicar.
2. Pruebe la inserción y limpieza de una fila temporal sin mostrar su contenido.
3. Active DVWA solo tras esa prueba y publique para un único grupo piloto.
4. Desde Purple, realice el ejercicio exclusivamente en DVWA y en la fila de
   corrida indicada por la plataforma. Cierre el reto y confirme que se elimina
   solo esa fila.

Si cualquiera de los pasos falla, despublique el reto o déjelo deshabilitado;
no reinicie DVWA, MariaDB ni restaure un snapshot con corridas activas.
