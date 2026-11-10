# 02. Respaldar y actualizar la plataforma operativa

Esta guía conserva la BD actual. No utiliza la secuencia de limpieza de `DocumentacionBD`. Antes de actualizar, acuerda una ventana de mantenimiento, drena los recursos y espera que sus corridas queden liberadas según [01](01_RESTAURACION_SNAPSHOTS.md).

## 1. Acceso y requisitos del respaldo

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

En LAB-CTFWEB:

```bash
cd /ctf-plataform/ || exit 1
command -v pg_dump pg_restore
pg_dump --version
pg_restore --version
```

Usa clientes compatibles con PostgreSQL 16. Si faltan, solicita al administrador instalar el cliente de esa versión desde el repositorio de paquetes aprobado; no necesitas un servidor PostgreSQL adicional. El respaldo debe quedar en almacenamiento con espacio suficiente y copia fuera de la VM web.

## 2. Configurar una vez el acceso privado de pg_dump

Como tu cuenta Linux habitual de LAB-CTFWEB:

```bash
umask 077
touch ~/.pg_service.conf ~/.pgpass
chmod 600 ~/.pg_service.conf ~/.pgpass
nano ~/.pg_service.conf
```

Agrega esta sección conservando las demás. Si `[cociber]` ya existe, revisa sus valores sin duplicarla:

```ini
[cociber]
host=10.10.10.14
port=5432
dbname=cociber_fresh
user=cociber_app
sslmode=require
```

Guarda con Ctrl+O, Enter y Ctrl+X. `sslmode=require` conserva el modo de laboratorio; si ya tienes una CA y `verify-full` operativos, conserva esa configuración verificada.

```bash
nano ~/.pgpass
```

Agrega una línea con la contraseña **real de aplicación** en lugar del marcador:

```text
10.10.10.14:5432:cociber_fresh:cociber_app:CONTRASENA_PRIVADA_REAL
```

Si la contraseña contiene `:` o `\`, esos caracteres se escriben escapados como `\:` o `\\` en `.pgpass`. No publiques estos archivos. No ejecutes el backup con sudo: la configuración pertenece a la cuenta Linux que acabas de utilizar.

## 3. Crear y comprobar un respaldo

Indica un directorio **exclusivo** de respaldos en un almacenamiento previamente montado y con permiso de escritura para tu cuenta. El script conserva siete días y elimina únicamente sus archivos `cociber-*.dump` antiguos después de producir un respaldo nuevo válido.

```bash
read -rp 'Ruta absoluta del directorio exclusivo de respaldos: ' backup_dir
test -d "$backup_dir" && test -w "$backup_dir" && df -h "$backup_dir"
```

Si la comprobación falla, detente y solicita preparar el directorio/montaje; no cambies la ruta por `/` o por una carpeta de datos del motor. Con la ruta revisada:

```bash
PGSERVICE=cociber PGPASSFILE="$HOME/.pgpass" BACKUP_DIR="$backup_dir" bash scripts/backup_db.sh
```

Esperado: `Backup validado:` y la ruta del dump. Copia esa ruta para registrar la revisión:

```bash
read -rp 'Ruta exacta del dump recién creado: ' backup_file
pg_restore --list "$backup_file"
sha256sum "$backup_file"
```

Listar el contenido comprueba que el archivo es legible, pero no reemplaza una restauración ensayada en una base aislada. El dump respalda la base de aplicación; conserva también, por los procedimientos del administrador, roles de PostgreSQL, configuración privada, claves y datos de Guacamole. No restaures un ensayo sobre `cociber_fresh` en servicio.

## 4. Actualizar API, web y worker

Con el respaldo verificado y sin corridas vivas, sigue [actualización de interfaz y Guacamole](../01_Plataforma/02_ACTUALIZAR_INTERFAZ_Y_GUACAMOLE.md): revisar el código, detener el worker si estaba activo, construir, comprobar y recrear API/web, y volver a iniciar el worker. Ese documento incluye los comandos y la comprobación en navegador.

Si una versión futura modifica el esquema, prepara su migración y restauración por separado antes de actualizar. El script de actualización del repositorio no convierte automáticamente esquemas ni elimina datos.

## 5. Comprobación posterior y diagnóstico

En LAB-CTFWEB, dentro de `/ctf-plataform/`:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli check
sudo systemctl status cociber-fresh-worker.service --no-pager
sudo journalctl -u cociber-fresh-worker.service -n 60 --no-pager
```

Si todavía no has preparado los laboratorios, el worker puede no estar instalado: continúa con [la secuencia de laboratorios](../02_Laboratorios/01_REQUISITOS_Y_TRANSFERENCIA.md) cuando corresponda. Si ya había prácticas habilitadas, el worker debe quedar activo antes de reabrirlas.

Comprueba login, inventario de Guacamole y una corrida de prueba. Guarda versión de código, fecha y resultado; no incluyas contraseñas, tokens ni banderas en el registro compartido.
