# 05. Preparar LAB-SRVWEB para ESC-03

**Antes:** [01. Transferencia](01_REQUISITOS_Y_TRANSFERENCIA.md), [02. Claves](02_CUENTA_TECNICA_Y_CLAVES.md), snapshot previo y ninguna corrida activa en la víctima. Esta guía integra una instalación **DVWA ya existente** en `10.10.30.20`; no instala ni reinicia sus datos de ejemplo. Si DVWA todavía no está instalado, deja ESC-03 deshabilitado y registra ese requisito pendiente.

## 1. Acceder y comprobar los servicios

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
```

En LAB-SRVWEB:

```bash
hostname
id labops
command -v python3 mariadb
sudo ss -lntp '( sport = :80 )'
sudo mariadb --batch --skip-column-names -e 'SELECT VERSION(), CURRENT_USER();'
```

El último comando debe entrar como administrador local sin pedir contraseña de MariaDB: el helper usa esa misma vía de socket como root. Si falla, el administrador de BD debe revisar la autenticación local; no añadas la contraseña a los argumentos del helper.

Desde el navegador de Kali verifica `http://10.10.30.20/dvwa/` y entra con la cuenta de práctica entregada por el instructor. No uses «Create / Reset Database» sobre una instalación en uso. Si la URL real es otra, registra la correcta en las instrucciones del reto antes de continuar.

## 2. Revisar si existe una tabla del esquema anterior

```bash
sudo mariadb --batch -e "SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='ctf_app_db' AND TABLE_NAME='secrets';"
```

Si devuelve una fila, revisa su definición:

```bash
sudo mariadb -e 'SHOW CREATE TABLE ctf_app_db.secrets\G'
```

El helper nuevo necesita `run_id` como clave primaria de 12 caracteres y `flag` de al menos 55 caracteres. La tabla antigua con `id` numérico **no es compatible**. Si encuentras ese esquema, detente: conserva su respaldo y acuerda una sustitución o migración separada antes de continuar. No ejecutes DROP ni ALTER copiando instrucciones de la versión histórica.

**Solo si la tabla no existe**, crea la estructura nueva:

```bash
sudo mariadb <<'SQL'
CREATE DATABASE IF NOT EXISTS ctf_app_db;
CREATE TABLE ctf_app_db.secrets (
  run_id CHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  flag VARCHAR(128) NOT NULL
);
SQL
```

## 3. Permitir lectura desde la cuenta SQL de DVWA

Identifica la cuenta y host **reales** de la conexión que usa DVWA en su configuración privada. No compartas su contraseña. El login de la página DVWA no es necesariamente su usuario SQL.

Abre la consola administrativa:

```bash
sudo mariadb
```

En las siguientes sentencias sustituye `USUARIO_SQL_DVWA` y `HOST_SQL_DVWA` por esa cuenta existente; no ejecutes los marcadores literalmente:

```sql
SHOW GRANTS FOR 'USUARIO_SQL_DVWA'@'HOST_SQL_DVWA';
GRANT SELECT ON ctf_app_db.secrets TO 'USUARIO_SQL_DVWA'@'HOST_SQL_DVWA';
SHOW GRANTS FOR 'USUARIO_SQL_DVWA'@'HOST_SQL_DVWA';
exit
```

Esto agrega lectura sobre la evidencia. Si la cuenta ya tiene permisos globales de escritura, el GRANT no los reduce: revisa con el administrador cómo limitarla sin romper DVWA. La escritura de flags corresponde exclusivamente al helper local.

## 4. Instalar y validar el helper

En la terminal Linux de LAB-SRVWEB:

```bash
sudo install -o root -g root -m 0755 /tmp/ctf-lab-helper.py /usr/local/sbin/ctf-dvwa-lab
sudo python3 -m py_compile /usr/local/sbin/ctf-dvwa-lab
sudo EDITOR=nano visudo -f /etc/sudoers.d/cociber-fresh
```

Escribe una línea completa y guarda con Ctrl+O, Enter y Ctrl+X:

```sudoers
labops ALL=(root) NOPASSWD: /usr/local/sbin/ctf-dvwa-lab create *, /usr/local/sbin/ctf-dvwa-lab check *, /usr/local/sbin/ctf-dvwa-lab destroy *
```

Valida:

```bash
sudo chmod 0440 /etc/sudoers.d/cociber-fresh
sudo visudo -cf /etc/sudoers.d/cociber-fresh
sudo -u labops sudo -n -l
```

Esperado: sintaxis correcta y permiso para las tres acciones. No edites el Python con tabulaciones ni reutilices `ctf-dvwa-flag --upsert ID`: ese contrato es histórico. El helper nuevo recibe la flag por entrada estándar solo en `create`; `check` y `destroy` no esperan entrada. La prueba automática del siguiente documento comprueba todo el ciclo sin mostrar una bandera real.

Siguiente: [06. Pruebas y worker](06_PRUEBAS_Y_WORKER.md).
