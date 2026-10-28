# CoCiber CTF · actualización automática desde GitHub main

**Servidor objetivo:** VM de aplicación `10.10.10.13`, donde se ejecuta `docker-compose.prod.yml` con contenedores `api` y `web`.  
**Servidores NO modificados:** LAB-GUAC (Guacamole en VM independiente), PostgreSQL y Redis `10.10.10.14`, proxy HTTPS de `10.195.20.21`, y las VMs Kali/víctimas de Nutanix.

## Qué hace la automatización

Un temporizador de Linux (`systemd`) consulta `origin/main` **cada ~2 minutos**, sin exponer SSH ni Docker a internet. Cuando detecta un commit nuevo:

1. Exige que el directorio del proyecto esté limpio y en `main`. No usa `git push --force` ni sobrescribe ediciones locales.
2. Comprueba que el nuevo commit puede incorporarse por **fast-forward**.
3. Consulta la API pública de GitHub Actions y exige que el workflow **`ctf-quality.yml` haya terminado con `success` para ese SHA exacto**, en un evento `push` a `main`. Si no pasó o aún se ejecuta, espera al próximo ciclo.
4. Comprueba que el despliegue actual funciona; valida el `docker-compose.prod.yml` existente.
5. Actualiza el código y reconstruye **solo** `api` y `web`:
   `docker compose -f docker-compose.prod.yml build api web` y `up -d --no-deps api web`.
6. Comprueba la respuesta `/api/v1/health` del servidor `10.10.10.13:8081` y la conectividad a **PostgreSQL/Redis** desde el contenedor API.
7. Si el despliegue falla, intenta restaurar automáticamente el commit anterior y reconstruir esos dos contenedores. Si el rollback también falla, deja un error visible en el journal.
8. Consulta **en solo lectura** el inventario remoto de Guacamole. Si no responde, advierte del problema **sin crear, eliminar ni sobrescribir conexiones existentes**.

El proyecto guarda la relación entre las VMs y los identificadores de Guacamole, pero **las conexiones y contraseñas permanecen en la BD independiente de Guacamole**. No se debe resembrar ese servidor al actualizar la web.

### Advertencias importantes antes de activar

- **Rotar credenciales y secretos expuestos:** si un `.env` con contraseñas reales se compartió en un chat u otro canal, cambia contraseñas de PostgreSQL, Redis, Guacamole y cuentas SSH de inyector; crea una cuenta técnica propia en Guacamole con permisos mínimos. Planifica la rotación de `JWT_SECRET` y `FIELD_HMAC_SECRET` con respaldos, pues puede invalidar sesiones o evidencias de retos existentes.
- Cambia `FLAG_INJECTOR_STRICT_HOST_KEY=false` a validación `true` y configura `known_hosts` verificado antes de operación normal.
- **No** guardes `.env`, tokens ni contraseñas en Git. El `.env` actual permanece en la VM y está excluido por `.gitignore`.
- Protege `main` en GitHub (revisión de cambios, CI obligatorio y accesos mínimos); aprobar una modificación en `main` equivale a autorizar su despliegue automático a un servidor con Docker.
- Haz y verifica respaldos de PostgreSQL/Redis antes de empezar. El script no crea backups ni aplica **migraciones de esquema**, porque `MANAGE_SCHEMA_ON_STARTUP=false` debe conservarse. Una migración que requiera intervención no debe ejecutarse por este mecanismo.
- El endpoint `/health` comprueba API; las pruebas posteriores comprueban PostgreSQL/Redis, pero **no constituyen una prueba completa** de usuarios, grupos, sesiones y Guacamole.
- **No corrige el certificado TLS** de `https://10.195.20.21`. Para `ERR_CERT_AUTHORITY_INVALID` sigue `Docs/RECUPERACION_TLS_GUACAMOLE_PRODUCCION.md`.

## Instalación inicial (UNA SOLA VEZ, en 10.10.10.13)

Abre una terminal SSH con permisos administrativos en la VM web de producción. Entra al **directorio real del clon Git existente** (el que contiene `docker-compose.prod.yml` y el `.env` privado). Los comandos aquí no crean ni reemplazan secretos:

```bash
pwd
git status --short
git branch --show-current
git remote -v
```

Si `git status` muestra modificaciones, revisa esas diferencias **antes** de continuar. No utilices `git reset --hard` para forzar la actualización inicial; conserva los datos del usuario.

Cuando esté limpio y estés en `main`:

```bash
git fetch origin
git pull --ff-only origin main

sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml ps

sudo bash scripts/instalar_auto_deploy_main.sh "$PWD"
```

El instalador:

- Copia el script estable a `/usr/local/sbin/cociber-auto-deploy-main` con propiedad de `root`.
- Crea `/etc/cociber-ctf/auto-deploy.conf` como archivo `root:root`, permisos `0600` (**sin** las contraseñas del `.env`). Si existe, **lo conserva**.
- Instala y habilita las unidades `cociber-ctf-auto-deploy.service` y `.timer`.
- No ejecuta `docker compose down`, ni `docker volume prune`, ni configura un nuevo Guacamole.

**El usuario del clon Git** se obtiene del propietario del directorio y se usa solo para `git fetch/merge`. Las operaciones de Docker se ejecutan desde el servicio root-owned. Un miembro del grupo Docker obtiene privilegios equivalentes a root; restringe quién puede modificar el repositorio y el instalador.

### Confirmar que quedó activado

```bash
sudo systemctl status cociber-ctf-auto-deploy.timer --no-pager
sudo systemctl list-timers cociber-ctf-auto-deploy.timer
sudo journalctl -u cociber-ctf-auto-deploy.service -n 80 --no-pager
```

Para **ejecutar una revisión y despliegue en el momento**, siempre que esté preparado para una actualización real:

```bash
sudo systemctl start cociber-ctf-auto-deploy.service
sudo journalctl -u cociber-ctf-auto-deploy.service -n 100 --no-pager
```

El servicio se ejecuta a intervalos automáticamente. En una actualización normal, el proceso puede mostrar que no hay cambios, que CI está pendiente o que una versión fue desplegada.

### Pausar y reactivar sin tocar datos

```bash
# Pausar la automatización temporalmente:
sudo systemctl disable --now cociber-ctf-auto-deploy.timer

# Reactivar:
sudo systemctl enable --now cociber-ctf-auto-deploy.timer
```

En una ventana de mantenimiento también puedes bloquear nuevas ejecuciones mientras inspeccionas logs o actualizas el certificado TLS.

## Cómo funciona en las siguientes actualizaciones

A partir de la instalación, cuando se fusionan cambios en `main`, GitHub Actions ejecuta pruebas del frontend, backend y scripts. Si terminan con éxito, el servicio de la VM detectará el SHA nuevo y actualizará `api` y `web`. **No tienes que ejecutar `git pull` en cada cambio**.

La copia instalada en `/usr/local/sbin` es estable: una edición del propio script de despliegue en GitHub **no se ejecutará como root automáticamente**. Para actualizar el instalador en una intervención planificada, vuelve a ejecutar:

```bash
sudo bash scripts/instalar_auto_deploy_main.sh "$PWD"
```

Los dos contenedores CoCiber pueden reiniciarse durante la actualización, por lo que se debe programar el despliegue fuera de una evaluación o clase activa.

## Diagnóstico

- **CI pending:** el workflow aún se ejecuta o no existe un run válido para el SHA. Esperar/revisar la pestaña Actions del repositorio.
- **CI failure:** corregir el código en GitHub antes de desplegar.
- **Clon sucio o divergente:** revisar `git status` y la rama local. El script **no** borra trabajo local.
- **Sin acceso a GitHub:** comprobar DNS/salida HTTPS del servidor `10.10.10.13` hacia `github.com` y `api.github.com`.
- **Falló el healthcheck:** revisar `docker compose -f docker-compose.prod.yml logs --tail=100 api web` y logs del temporizador.
- **No responden PostgreSQL/Redis:** comprobar `10.10.10.14`, ACL, usuario y servicios desde el contenedor API. No cambiar la BD automáticamente.
- **Guacamole inaccesible:** comprobar `GUACAMOLE_MODE=real`, URLs administrativas, cuenta técnica y conectividad **desde el contenedor API**; no recrear conexiones. El script reporta el problema sin modificar Guacamole.
- **`ERR_CERT_AUTHORITY_INVALID`:** fallo del certificado del proxy TLS en `10.195.20.21`, independiente del código de la web.

### Revisión segura del estado de la aplicación

```bash
sudo docker compose -f docker-compose.prod.yml ps
curl --fail --show-error --silent http://10.10.10.13:8081/api/v1/health
sudo journalctl -u cociber-ctf-auto-deploy.service -n 100 --no-pager
```

**No pegues salidas que incluyan secretos, tokens, URLs de BD con usuario/contraseña o contenidos de `.env`.** Si necesitas soporte, envía estado/errores sin credenciales.

## Archivos incorporados

| Archivo | Función |
|---|---|
| `scripts/cociber_auto_deploy_main.sh` | Detectar main, validar CI exacto, actualizar y hacer rollback |
| `scripts/instalar_auto_deploy_main.sh` | Instalador inicial de root y systemd |
| `deploy/systemd/cociber-ctf-auto-deploy.service` | Servicio seguro, una ejecución |
| `deploy/systemd/cociber-ctf-auto-deploy.timer` | Revisar cada ~2 minutos |
| `scripts/qa/check_auto_deploy.py` | Comprobación estática en GitHub Actions |
