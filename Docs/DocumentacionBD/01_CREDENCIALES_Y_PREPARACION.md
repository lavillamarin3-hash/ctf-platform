# 01. Preparación y credenciales de las bases de datos

> **Secuencia condicionada de BD.** La plataforma actual ya conecta correctamente: no repitas limpieza ni inicialización para preparar los laboratorios. Usa esta carpeta solamente para un reinicio deliberado de datos con respaldo, siguiendo su [paso 01](01_CREDENCIALES_Y_PREPARACION.md). Para continuar la instalación operativa vuelve al [índice principal](../00_Inicio/01_LEEME_PRIMERO.md).
>
> Antes de ejecutar comandos, abre la sesión del servidor indicado en cada sección mediante [acceso SSH y comandos base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). En LAB-CTFWEB ejecuta `cd /ctf-plataform/ || exit 1`; en LAB-DB-POSTGRES no se necesita esa carpeta. Si una sección cambia de servidor, abre otra terminal SSH y verifica `hostname`.

## Acceso previo al servidor de datos

Desde PowerShell local, escribe la cuenta **Linux** real cuando se solicite:

```powershell
$CuentaBD = Read-Host 'Cuenta Linux administrativa de LAB-DB-POSTGRES'
ssh -J lab-rtrfw@10.195.20.20 "$($CuentaBD)@10.10.10.14"
```

Ya dentro de LAB-DB-POSTGRES, confirma el equipo antes de revisar credenciales o motores:

```bash
hostname
ip -brief address
```

Debe corresponder a `10.10.10.14`. Para editar, abre el archivo con el comando indicado; en Nano guarda con Ctrl+O, Enter y Ctrl+X. Los bloques `sql` se ejecutan dentro del cliente de BD, no directamente en Bash. Los bloques con `<<'SQL'` se copian completos desde Bash.



Actualizado: **9 de noviembre de 2026**. Procedimiento para sustituir los datos de la plataforma anterior por una instalación nueva, conservando PostgreSQL, Redis y las credenciales acordadas. Los comandos se entregan para ejecutarlos por etapas; no se han ejecutado en el servidor.

## Orden de trabajo

| Paso | Documento | Dónde se ejecuta |
| --- | --- | --- |
| 01 | Este documento: alcance y credenciales | Administración |
| 02 | [Servidor y almacenamiento](02_SERVIDOR_Y_ALMACENAMIENTO.md) | LAB-DB-POSTGRES |
| 03 | [Mantenimiento y respaldo](03_MANTENIMIENTO_Y_RESPALDO.md) | Primero LAB-CTFWEB, después LAB-DB-POSTGRES |
| 04 | [Limpieza y PostgreSQL 16 nuevo](04_LIMPIEZA_Y_POSTGRESQL_16.md) | LAB-DB-POSTGRES |
| 05 | [Limpieza y permisos de Redis 7](05_LIMPIEZA_Y_REDIS_7.md) | LAB-DB-POSTGRES |
| 06 | [Conectar la plataforma nueva](06_CONTINUAR_INSTALACION.md) | LAB-CTFWEB |
| 07 | [Validación y recuperación](07_VALIDACION_Y_RECUPERACION.md) | Ambos servidores |

## Qué se conserva y qué se limpia

| Elemento | Anterior, según las guías | Destino nuevo |
| --- | --- | --- |
| Servidor de datos | 10.10.10.14, PostgreSQL 16 y Redis 7 nativos | El mismo |
| Base PostgreSQL | `cociber_ctf` | `cociber_fresh` |
| Redis lógico | `/0`, según el generador antiguo de conexiones | `/1`, vacío y reservado para la versión nueva |
| Administrador de ambos motores | `cociberctf` | Se conserva |
| Cuenta de aplicación de ambos motores | `cociber_app` | Se conserva |
| Datos de usuarios, retos y puntuaciones | Instalación anterior | No se importan a la nueva |

Los nombres anteriores se deducen de los archivos entregados, no de una inspección remota. Confirma que la configuración privada activa usa esos destinos. Si aparece otra base o un índice Redis diferente, no sustituyas nombres a ciegas: registra primero a qué aplicación pertenece.

La limpieza elimina **solo `cociber_ctf` y las claves del índice Redis antiguo confirmado como exclusivo del CTF**. Conserva roles SQL, usuarios ACL de Redis, servicios, paquetes, cluster, archivos de configuración y discos. No afecta MariaDB de Guacamole en 10.10.10.10 ni la base de DVWA en 10.10.30.20.

## Credenciales que se mantienen

| Variable | Valor o tratamiento |
| --- | --- |
| `PG_ADMIN_USER` | `cociberctf` |
| `REDIS_ADMIN_USER` | `cociberctf` |
| `PG_APP_USER` | `cociber_app` |
| `REDIS_APP_USER` | `cociber_app` |
| `PG_ADMIN_PASSWORD` | Conservar la contraseña PostgreSQL indicada por el operador |
| `REDIS_ADMIN_PASSWORD` | Conservar la contraseña Redis indicada por el operador |
| `PG_APP_PASSWORD` / `REDIS_APP_PASSWORD` | Conservar el mismo valor de aplicación indicado por el operador para ambos motores |

Estas guías **no rotan ni regeneran** las contraseñas. Los valores reales se introducen de forma privada cuando se solicitan y no se copian a Markdown ni Git. El archivo anterior `/etc/cociber-ctf/deploy-secrets.env`, si existe, sigue siendo la referencia privada; no lo reemplaces con una plantilla.

```bash
sudo stat -c '%U:%G %a %n' /etc/cociber-ctf/deploy-secrets.env
sudoedit /etc/cociber-ctf/deploy-secrets.env
```

Revisa los nombres anteriores y sus valores existentes. No necesitas cambiar el archivo para borrar una base, ni cargarlo con `source`. Si no existe, las operaciones de esta secuencia admiten autenticación interactiva; no dependen del repositorio antiguo de despliegue.

`cociberctf` es una cuenta administrativa de los motores, no el usuario Linux ni el administrador web. En PostgreSQL se conserva su condición de superusuario. La API usa `cociber_app`, con acceso a tablas y sin privilegios de superusuario.

## Qué reemplaza esta secuencia

Se revisaron los documentos `00_CREDENCIALES_Y_PREPARACION.md`, `01_SERVIDOR_Y_ALMACENAMIENTO.md`, `02_POSTGRESQL_16.md`, `03_REDIS_7.md` y `07_CONTINUAR_INSTALACION.md` del paquete `cociber-ctf-deploy` entregado por el operador. Las copias originales permanecen intactas fuera de este repositorio.

Para este reinicio **no ejecutes de nuevo** `bootstrap-database.sh`, `sql/01_schema.sql`, `configure-postgresql.sh --apply`, `configure-redis.sh --apply` ni `write_application_env.py` del paquete antiguo. Crean el esquema anterior o pueden restaurar permisos, nombres y conexiones antiguos. El esquema de esta secuencia es exclusivamente [cociber_fresh.sql](../../deploy/schema/cociber_fresh.sql). Usa el archivo del mismo checkout que desplegarás.
