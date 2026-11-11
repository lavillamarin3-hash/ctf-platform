# 02. Preparar labops, su clave y las huellas de host

**Antes:** [archivos transferidos](01_REQUISITOS_Y_TRANSFERENCIA.md) y acceso de mantenimiento comprobado. Realiza esta guía en LNXVICT, SRVWEB y cada Kali que usarás. No actives todavía los inyectores.

## 1. Crear o conservar la clave en LAB-CTFWEB

Conéctate como indica [acceso base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). En LAB-CTFWEB:

```bash
cd /ctf-plataform/ || exit 1
sudo install -d -o root -g 10001 -m 0750 /opt/cociber-secrets
sudo ls -l /opt/cociber-secrets/labops_ed25519 /opt/cociber-secrets/labops_ed25519.pub
```

Si ambos archivos ya existen, consérvalos y omite `ssh-keygen`. Si **no existe ninguno**, créalos:

```bash
sudo ssh-keygen -t ed25519 -f /opt/cociber-secrets/labops_ed25519 -N '' -C 'cociber-fresh-labops'
```

Si existe solo uno de los dos, detente y revisa el par; no sobrescribas una clave desplegada. Ajusta permisos para la API, que usa el UID/grupo numérico 10001:

```bash
sudo chown root:10001 /opt/cociber-secrets/labops_ed25519
sudo chmod 0640 /opt/cociber-secrets/labops_ed25519
sudo install -o root -g root -m 0644 /opt/cociber-secrets/labops_ed25519.pub /tmp/cociber-labops.pub
```

`/opt/cociber-secrets` es la ubicación de los secretos, **no la del proyecto**. Se conserva porque el Compose la monta como `/run/secrets` en la API.

## 2. Copiar exclusivamente la clave pública

En LAB-CTFWEB:

```bash
scp /tmp/cociber-labops.pub lab-lnxvict@10.10.30.12:/tmp/cociber-labops.pub
scp /tmp/cociber-labops.pub lab-srvweb@10.10.30.20:/tmp/cociber-labops.pub
scp /tmp/cociber-labops.pub lab-kali-blue@10.10.20.12:/tmp/cociber-labops.pub
```

Si también preparas Purple, ejecuta desde LAB-CTFWEB:

```bash
scp /tmp/cociber-labops.pub lab-kali-purple@10.10.20.11:/tmp/cociber-labops.pub
```

Si preparas LAB-KALI:

```bash
scp /tmp/cociber-labops.pub lab-kali@10.10.20.10:/tmp/cociber-labops.pub
```

Introduce la contraseña de mantenimiento de cada VM cuando se solicite. Estas cuentas administrativas instalan la clave pública para `labops`; no cambies `SSH_INJECTOR_USER=labops` por el usuario administrativo de Kali. **Nunca transfieras `labops_ed25519` sin `.pub` a las víctimas.**

## 3. Crear o revisar labops en cada VM

Dentro de cada VM, comprueba primero `hostname` e `id labops`:

```bash
hostname
id labops
```

Solo si devuelve «no such user», crea la cuenta en esa VM:

```bash
sudo adduser --disabled-password --gecos '' labops
```

No agregues `labops` al grupo sudo; sus permisos se limitarán a helpers concretos. Si la cuenta existe, conserva su home, claves y permisos anteriores. Para añadir la clave pública sin reemplazar `authorized_keys`:

```bash
labops_home=$(getent passwd labops | cut -d: -f6)
labops_group=$(id -gn labops)
printf 'Home de labops: %s\n' "$labops_home"
test -n "$labops_home" && test -d "$labops_home"
```

Comprueba que sea el home real de labops; no continúes si está vacío, es `/` o pertenece a otra cuenta. Después:

```bash
sudo install -d -o labops -g "$labops_group" -m 0700 "$labops_home/.ssh"
sudo -u labops touch "$labops_home/.ssh/authorized_keys"
sudo grep -qxF -f /tmp/cociber-labops.pub "$labops_home/.ssh/authorized_keys" || sudo tee -a "$labops_home/.ssh/authorized_keys" < /tmp/cociber-labops.pub
sudo chown labops:"$labops_group" "$labops_home/.ssh/authorized_keys"
sudo chmod 0600 "$labops_home/.ssh/authorized_keys"
sudo stat -c '%U:%G %a %n' "$labops_home/.ssh" "$labops_home/.ssh/authorized_keys"
```

Esperado: propietario labops, directorio 700 y archivo 600. La salida de `tee`, si aparece, es una **clave pública**. Si existe una política AllowUsers/AllowGroups, el administrador debe permitir a labops sin borrar las restricciones vigentes.

## 4. Registrar la identidad de cada host

En la consola administrativa confiable de **cada VM**, anota IP, hostname y huella:

```bash
hostname
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Vuelve a LAB-CTFWEB y recoge candidatos para **las VM que realmente preparaste**. Este ejemplo incluye las tres Kali y las dos víctimas; si todavía no prepararás alguna, omite su IP tanto en la captura como en las comprobaciones posteriores:

```bash
ssh-keyscan -T 5 -t ed25519 10.10.20.10 10.10.20.12 10.10.20.11 10.10.30.12 10.10.30.20 > /tmp/cociber-known-hosts-candidatos
ssh-keygen -lf /tmp/cociber-known-hosts-candidatos
```

**`>` reemplaza todo el archivo de candidatos.** No ejecutes después otra captura de una sola IP con `>` sobre el mismo archivo: perderías las entradas anteriores. Si faltó una VM, vuelve a capturar la lista completa. Capturar no modifica el archivo definitivo `/opt/cociber-secrets/known_hosts`.

Compara cada huella con la de su consola. `ssh-keyscan` por sí solo no acredita identidad. Esperado para este ejemplo: cinco entradas con sus cinco IP. Si falta un host o una huella no coincide, corrige el acceso o consulta al responsable; no continúes ni desactives la verificación.

**Solo después de verificar las huellas**, ejecuta completo el siguiente bloque en LAB-CTFWEB. El bloque elige automáticamente qué hacer: si existe known_hosts, lo respalda y agrega las entradas comprobadas; si no existe, lo crea. No necesitas ejecutar dos alternativas manualmente. Si falla el respaldo, se detiene antes de modificar el archivo.

Si un host ya registrado tiene ahora otra huella, detente y confirma el motivo con el responsable antes de agregarla. Este procedimiento no resuelve ni elimina por sí solo identidades cambiadas.

```bash
sudo bash <<'BASH'
set -eu
candidatos=/tmp/cociber-known-hosts-candidatos
destino=/opt/cociber-secrets/known_hosts
test -s "$candidatos"
ssh-keygen -lf "$candidatos"
if [ -e "$destino" ]; then
  cp -a -- "$destino" "${destino}.$(date -u +%Y%m%dT%H%M%S%N).bak"
  printf '\n' >> "$destino"
  cat -- "$candidatos" >> "$destino"
else
  install -o root -g 10001 -m 0640 "$candidatos" "$destino"
fi
chown root:10001 "$destino"
chmod 0640 "$destino"
printf '\nHuellas instaladas en %s:\n' "$destino"
ssh-keygen -lf "$destino"
BASH
```

Comprueba el **archivo definitivo**, no solamente el de candidatos:

```bash
for vm_ip in 10.10.20.10 10.10.20.12 10.10.20.11 10.10.30.12 10.10.30.20; do
  printf '\nDestino %s\n' "$vm_ip"
  sudo ssh-keygen -F "$vm_ip" -f /opt/cociber-secrets/known_hosts || printf 'FALTA esta IP: no continúes con su autenticación.\n'
done
```

Cada IP preparada debe mostrar su entrada `ssh-ed25519`. Repetir la incorporación puede dejar entradas idénticas duplicadas; no significa que haya más VM. Lo importante es que cada IP tenga la clave verificada correcta.

**Caso observado el 10 de noviembre de 2026:** la segunda captura, solo de `10.10.20.10`, sobrescribió el archivo temporal. Después se instaló ese archivo con una única entrada. Volver a capturar las cinco IP no actualizó known_hosts, porque faltaba ejecutar la incorporación de este paso. No era un fallo de la contraseña ni de la clave privada de labops.

## 5. Probar una autenticación real desde LAB-CTFWEB

**Antes:** el paso 4 debe haber instalado y comprobado las huellas en `/opt/cociber-secrets/known_hosts`. Los siguientes comandos usan rutas absolutas y pueden ejecutarse desde cualquier carpeta de LAB-CTFWEB; no requieren `sudo su`.

OpenSSH ejecutado como root puede rechazar la clave privada 0640. Usa esta copia temporal 0600 para la prueba manual; la original sigue legible por el contenedor:

```bash
sudo install -o root -g root -m 0600 /opt/cociber-secrets/labops_ed25519 /run/cociber-labops-prueba
sudo ssh -i /run/cociber-labops-prueba -o IdentitiesOnly=yes -o BatchMode=yes -o UserKnownHostsFile=/opt/cociber-secrets/known_hosts -o StrictHostKeyChecking=yes labops@10.10.30.12 'id -un'
```

Esperado: `labops`, sin solicitar contraseña. Repite el mismo comando cambiando solo el destino por SRVWEB y cada Kali preparada. Al finalizar:

```bash
sudo rm -f /run/cociber-labops-prueba
```

Si falla, distingue el tipo de error:

| Mensaje | Significado y siguiente paso |
| --- | --- |
| `No ED25519 host key is known` / `Host key verification failed` | Falta la identidad del destino o no coincide. Comprueba `sudo ssh-keygen -F 10.10.30.12 -f /opt/cociber-secrets/known_hosts` y completa el paso 4. Todavía no se ha autenticado a labops. |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Hay una identidad diferente de la registrada; confirma si hubo restauración o reinstalación antes de modificar las huellas. |
| `Permission denied (publickey)` | Ya se superó la identidad del servidor, pero falla el acceso de labops: revisa la clave pública instalada, propietario/permisos y restricciones SSH del destino. |
| `Connection timed out` / `Connection refused` | Revisa acceso de red, IP, puerto 22 y servicio SSH del destino. |

Para revisar registros de una autenticación fallida hacia LNXVICT, abre **otra ventana PowerShell local** y entra a esa víctima con su cuenta administrativa:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
```

Ya en **LAB-LNXVICT**:

```bash
hostname
sudo journalctl -u ssh.service --since '10 minutes ago' --no-pager
```

Ejecutar ese journalctl en LAB-CTFWEB consulta su servidor SSH local, no el intento saliente hacia LNXVICT. Además, un rechazo de la huella ocurre en el cliente antes de autenticar al usuario. Si el destino usa otra unidad, consulta su nombre real. No publiques claves ni registros con secretos. Conserva las integraciones deshabilitadas hasta resolverlo.

Siguiente: [03. LNXVICT](03_LNXVICT_SSH.md).
