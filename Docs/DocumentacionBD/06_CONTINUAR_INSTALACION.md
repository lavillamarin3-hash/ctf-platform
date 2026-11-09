# 06. Conectar la plataforma nueva a las bases preparadas

Ejecutar en **LAB-CTFWEB, 10.10.10.13**, en el checkout actualizado de `ctf-platform`. Los capítulos 04 y 05 ya deben haber preparado `cociber_fresh`, su esquema y permisos, y Redis `/1` vacío. Los contenedores históricos permanecen detenidos.

## 1. Crear o revisar .env.fresh

```bash
cd ~/ctf-platform
cp -n deploy/fresh.env.example .env.fresh
chmod 600 .env.fresh
nano .env.fresh
```

Conserva la configuración SSH, Guacamole y demás campos siguiendo [la instalación nueva](../INSTALACION_NUEVA_COCIBER.md). No copies todo el `.env` histórico. La aplicación nueva lee **URLs**, no las variables sueltas `PG_APP_USER` y `REDIS_APP_USER` del instalador anterior.

Introduce la contraseña de aplicación que ya se acordó en **ambas** URLs, con el mismo usuario `cociber_app`. Nunca utilices aquí la contraseña administrativa de `cociberctf`.

```dotenv
DATABASE_URL=postgresql+asyncpg://cociber_app:CONTRASENA_APP_CODIFICADA@10.10.10.14:5432/cociber_fresh?ssl=require
REDIS_URL=redis://cociber_app:CONTRASENA_APP_CODIFICADA@10.10.10.14:6379/1
```

`CONTRASENA_APP_CODIFICADA` es una explicación, no un valor para dejar en el archivo. El bloque opcional siguiente escribe las dos líneas con codificación URL correcta, solicitando una sola vez la contraseña compartida de aplicación indicada por el operador. Conserva el resto de campos, respalda el archivo y no imprime secretos. No regenera contraseñas en los motores.

```bash
python3 - <<'PY'
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone
import getpass, os

path = Path('.env.fresh')
if path.is_symlink() or not path.is_file():
    raise SystemExit('Se requiere .env.fresh regular creado desde la plantilla.')
original = path.read_text(encoding='utf-8')
password = getpass.getpass('Contraseña EXISTENTE de cociber_app para ambos motores: ')
if not password or password != getpass.getpass('Repite la misma contraseña: '):
    raise SystemExit('Contraseñas vacías o diferentes; no se modificó el archivo.')
encoded = quote(password, safe='')
urls = {
    'DATABASE_URL': f'postgresql+asyncpg://cociber_app:{encoded}@10.10.10.14:5432/cociber_fresh?ssl=require',
    'REDIS_URL': f'redis://cociber_app:{encoded}@10.10.10.14:6379/1',
}
lines = [line for line in original.splitlines()
         if line.split('=', 1)[0].strip() not in urls]
backup = path.with_name('.env.fresh.antes-bd-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as stream:
    stream.write(original)
path.chmod(0o600)
path.write_text('\n'.join(lines + [f'{k}={v}' for k, v in urls.items()]) + '\n', encoding='utf-8')
print('URLs actualizadas; credenciales no mostradas. Respaldo privado:', backup.name)
PY
```

Si `.env.fresh` pertenece a root, utiliza `sudo python3` para ese bloque, conservando la misma carpeta de trabajo. Los respaldos `.env.fresh.*` también contienen secretos: se conservan fuera de Git. `ssl=require` corresponde al parámetro de **asyncpg**; no cambies a `sslmode=require` en esta URL. El cliente `psql`, en cambio, usa `sslmode` como se muestra en 04.

## 2. Completar configuración de la plataforma

```bash
nano .env.fresh
```

Completa `JWT_SECRET`, `PUBLIC_ORIGIN`, Guacamole y las rutas de claves según la guía principal. Mantén `BOOTSTRAP_ADMIN=false`, `SSH_INJECTOR_ENABLED=false`, `DVWA_LAB_ENABLED=false` y `WINRM_INJECTOR_ENABLED=false` durante la aceptación de las bases. Las integraciones de laboratorio se habilitan después de sus pruebas específicas.

No agregues `MANAGE_SCHEMA_ON_STARTUP` ni `CTF_SEED_DEMO_DATA`: pertenecen a la versión histórica. El esquema ya se cargó en 04; **omite `init-db --empty-database` de la guía principal**. No cargues nuevamente el SQL.

## 3. Construir y comprobar dependencias

```bash
sudo install -d -o root -g 10001 -m 0750 /opt/cociber-secrets
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml build api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli check
```

Esperado: `PostgreSQL y Redis: OK`. No ejecutes `docker compose config` sin `--quiet` para compartir su salida: podría mostrar las URLs privadas. Si la comprobación falla, usa [07](07_VALIDACION_Y_RECUPERACION.md) antes de arrancar.

## 4. Crear administrador web, arrancar y configurar catálogo

```bash
sudo bash scripts/crear_admin.sh
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml up -d --force-recreate --wait --wait-timeout 180 api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python reconcile_nutanix_inventory.py --fresh
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python reconcile_nutanix_inventory.py --fresh --apply
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli configure-catalog
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli configure-catalog --apply
```

La cuenta de administrador web es independiente de `cociberctf`; su contraseña se solicita al crearla. La primera entrada exige cambiarla. El catálogo se crea explícitamente en borrador; ESC-01/04/05 permanecen deshabilitados.

La nueva web escucha por defecto en `10.10.10.13:8081`. Revisa el proxy HTTPS existente antes de dirigirle la publicación de `10.195.20.21:443`; estas guías de bases no cambian DNAT ni TLS. Continúa los helpers, worker y demo en [INSTALACION_NUEVA_COCIBER.md](../INSTALACION_NUEVA_COCIBER.md), desde sus secciones correspondientes, sin repetir la inicialización de BD.

Siguiente: [07. Validación](07_VALIDACION_Y_RECUPERACION.md).
