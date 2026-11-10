# 04. Limpiar la base anterior y crear cociber_fresh

> **Secuencia condicionada de BD.** La plataforma actual ya conecta correctamente: no repitas limpieza ni inicialización para preparar los laboratorios. Usa esta carpeta solamente para un reinicio deliberado de datos con respaldo, siguiendo su [paso 01](01_CREDENCIALES_Y_PREPARACION.md). Para continuar la instalación operativa vuelve al [índice principal](../00_Inicio/01_LEEME_PRIMERO.md).
>
> Antes de ejecutar comandos, abre la sesión del servidor indicado en cada sección mediante [acceso SSH y comandos base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). En LAB-CTFWEB ejecuta `cd /ctf-plataform/ || exit 1`; en LAB-DB-POSTGRES no se necesita esa carpeta. Si una sección cambia de servidor, abre otra terminal SSH y verifica `hostname`.

Ejecutar en **LAB-DB-POSTGRES, 10.10.10.14**, después del respaldo y mantenimiento de [03](03_MANTENIMIENTO_Y_RESPALDO.md). Se reutiliza PostgreSQL 16; no se reinstala ni se elimina el cluster.

## 1. Confirmar el destino antes de borrar

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres -c "SELECT datname, pg_get_userbyid(datdba) AS propietario FROM pg_database WHERE datname IN ('cociber_ctf','cociber_fresh');"
```

La base histórica esperada es `cociber_ctf`. Si `cociber_fresh` ya existe, detente y verifica su contenido antes de borrar nada: puede corresponder a un intento previo o instalación utilizable. No se ofrece un borrado masivo por nombre parcial.

## 2. Eliminar exclusivamente cociber_ctf

Este bloque pide escribir el nombre exacto. Ejecutarlo elimina tablas, usuarios de la plataforma, corridas y puntuaciones de esa base; **no elimina los roles PostgreSQL ni cambia sus contraseñas**.

```bash
read -rp 'Con respaldo verificado y API detenida, escribe cociber_ctf para borrarla: ' confirmed_database
if [[ "$confirmed_database" == 'cociber_ctf' ]]; then
  sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -v ON_ERROR_STOP=1 -d postgres -c 'DROP DATABASE cociber_ctf;'
else
  printf 'Sin cambios.\n'
fi
unset confirmed_database
```

Si aparece «being accessed by other users», **no añadas FORCE**: vuelve a 03 y detén el consumidor pendiente. Si la base no existe, verifica el inventario; no cambies el nombre por otra base para conseguir que el comando pase. La operación se ejecuta conectada a `postgres`, fuera de una transacción. [Referencia de DROP DATABASE](https://www.postgresql.org/docs/16/sql-dropdatabase.html).

## 3. Conservar las cuentas existentes

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres -c "SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname IN ('cociberctf','cociber_app');"
```

Si están ambas y sus permisos son los esperados, **no ejecutes ALTER PASSWORD ni CREATE ROLE**. Una eliminación de base no obliga a cambiar credenciales.

Solo si falta una cuenta, abre `sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres`, crea **únicamente la ausente** y asigna interactivamente su contraseña ya acordada:

```sql
-- Solo si no existe cociberctf:
CREATE ROLE cociberctf LOGIN SUPERUSER;
\password cociberctf
-- Solo si no existe cociber_app:
CREATE ROLE cociber_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
\password cociber_app
\q
```

No copies ambos CREATE si solo falta uno. `\password` pide el valor sin escribirlo en el historial de sentencias. [Referencia de psql](https://www.postgresql.org/docs/16/app-psql.html).

## 4. Crear una base vacía nueva

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -v ON_ERROR_STOP=1 -d postgres <<'SQL'
CREATE DATABASE cociber_fresh OWNER cociberctf ENCODING 'UTF8' TEMPLATE template0;
REVOKE ALL ON DATABASE cociber_fresh FROM PUBLIC;
GRANT CONNECT ON DATABASE cociber_fresh TO cociber_app;
SQL
```

`CREATE DATABASE` falla si ya existe el destino; no uses una variante que lo borre primero. Su propietario administrativo será `cociberctf`. [Referencia de CREATE DATABASE](https://www.postgresql.org/docs/16/sql-createdatabase.html).

## 5. Cargar el esquema de este proyecto

Transfiere el esquema del mismo checkout que desplegarás. Abre **otra sesión SSH a LAB-CTFWEB** mediante [acceso base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). Desde ese servidor:

```bash
cd /ctf-plataform/ || exit 1
sha256sum deploy/schema/cociber_fresh.sql
read -rp 'Cuenta Linux administrativa de LAB-DB-POSTGRES: ' db_admin
scp deploy/schema/cociber_fresh.sql "${db_admin}@10.10.10.14:/tmp/cociber_fresh.sql"
unset db_admin
```

El rol SQL `cociberctf` no sustituye la cuenta Linux. Vuelve a la terminal de **LAB-DB-POSTGRES**, confirma `hostname` y ejecuta:

```bash
sha256sum /tmp/cociber_fresh.sql
```

El hash debe coincidir con el del servidor web. Solo entonces continúa en LAB-DB-POSTGRES:

```bash
sudo install -d -o root -g postgres -m 0750 /opt/cociber-fresh
sudo install -o root -g postgres -m 0640 /tmp/cociber_fresh.sql /opt/cociber-fresh/cociber_fresh.sql
sudo -u postgres sha256sum /opt/cociber-fresh/cociber_fresh.sql
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d cociber_fresh -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
```

El conteo debe ser **0**. Entonces carga el esquema bajo su propietario administrativo:

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -v ON_ERROR_STOP=1 -d cociber_fresh <<'SQL'
SET ROLE cociberctf;
\i /opt/cociber-fresh/cociber_fresh.sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO cociber_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cociber_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cociber_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cociberctf IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cociber_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cociberctf IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO cociber_app;
RESET ROLE;
SQL
```

Esta es la vía de inicialización elegida para toda la secuencia: **no ejecutar después `init-db --empty-database`**, porque el esquema ya existe. Tampoco cargar el `01_schema.sql` del repositorio antiguo. El SQL nuevo incluye las etiquetas de roles de la aplicación, pero no crea un administrador web.

## 6. Actualizar HBA conservando TLS y las restricciones de origen

Obtén la ruta con `SHOW hba_file` en 02. Si coincide con la guía original:

```bash
sudo cp -a /etc/postgresql/16/main/pg_hba.conf "/etc/postgresql/16/main/pg_hba.conf.antes-fresh.$(date -u +%Y%m%dT%H%M%S).bak"
sudoedit /etc/postgresql/16/main/pg_hba.conf
```

En las reglas **de `cociber_app`**, sustituye el nombre exacto `cociber_ctf` por `cociber_fresh`. Deben quedar antes de los rechazos correspondientes:

```text
local   cociber_fresh   cociber_app                     scram-sha-256
hostssl cociber_fresh   cociber_app   127.0.0.1/32        scram-sha-256
hostssl cociber_fresh   cociber_app   ::1/128             scram-sha-256
hostssl cociber_fresh   cociber_app   10.10.10.13/32      scram-sha-256
```

Conserva las reglas `postgres peer`, la administración local, los rechazos finales y cualquier regla de otro sistema. No reemplaces el archivo entero con este fragmento. No habilites el superusuario remoto desde la aplicación.

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres -c 'SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;'
```

Solo si devuelve cero errores:

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/psql -X -d postgres -c 'SELECT pg_reload_conf();'
/usr/lib/postgresql/16/bin/psql 'host=127.0.0.1 port=5432 dbname=cociber_fresh user=cociber_app sslmode=require' -W -c 'SELECT current_user, current_database(); SELECT rol_id, rol_nombre FROM "ROLES" ORDER BY rol_id;'
```

Usa la contraseña de aplicación existente. Esperado: `cociber_app`, `cociber_fresh` y cuatro roles. `sslmode=require` conserva el modo cifrado de laboratorio de la guía original; no valida por sí solo la identidad del servidor como `verify-full` con una CA adecuada.

Siguiente: [05. Redis 7](05_LIMPIEZA_Y_REDIS_7.md).
