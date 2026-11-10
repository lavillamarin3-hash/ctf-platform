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
read -rp 'Cuenta administrativa de LAB-KALI-BLUE: ' kali_admin
scp /tmp/cociber-labops.pub "${kali_admin}@10.10.20.12:/tmp/cociber-labops.pub"
unset kali_admin
```

Repite para Purple con `.11` y para cualquier otra Kali elegida. **Nunca transfieras `labops_ed25519` sin `.pub` a las víctimas.**

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

Vuelve a LAB-CTFWEB y recoge candidatos para **las VM que realmente preparaste**. Ejemplo Blue, Purple y las dos víctimas:

```bash
ssh-keyscan -T 5 -t ed25519 10.10.20.12 10.10.20.11 10.10.30.12 10.10.30.20 > /tmp/cociber-known-hosts-candidatos
ssh-keygen -lf /tmp/cociber-known-hosts-candidatos
```

Compara cada huella con la de su consola. `ssh-keyscan` por sí solo no acredita identidad. Si falta un host o una huella no coincide, corrige el acceso o consulta al responsable; no continúes ni desactives la verificación.

Solo después de la comparación, revisa si hay un archivo vigente:

```bash
sudo test -f /opt/cociber-secrets/known_hosts && sudo ssh-keygen -lf /opt/cociber-secrets/known_hosts
```

Si ya existe, respáldalo y **añade** las entradas comprobadas; no lo reemplaces ni elimines huellas antiguas por prueba y error:

```bash
sudo cp -a /opt/cociber-secrets/known_hosts "/opt/cociber-secrets/known_hosts.$(date -u +%Y%m%dT%H%M%S).bak"
sudo tee -a /opt/cociber-secrets/known_hosts < /tmp/cociber-known-hosts-candidatos > /dev/null
```

Si no existía, instala el archivo nuevo:

```bash
sudo install -o root -g 10001 -m 0640 /tmp/cociber-known-hosts-candidatos /opt/cociber-secrets/known_hosts
```

En ambos casos:

```bash
sudo chown root:10001 /opt/cociber-secrets/known_hosts
sudo chmod 0640 /opt/cociber-secrets/known_hosts
```

## 5. Probar una autenticación real desde LAB-CTFWEB

OpenSSH ejecutado como root puede rechazar la clave privada 0640. Usa esta copia temporal 0600 para la prueba manual; la original sigue legible por el contenedor:

```bash
sudo install -o root -g root -m 0600 /opt/cociber-secrets/labops_ed25519 /run/cociber-labops-prueba
sudo ssh -i /run/cociber-labops-prueba -o IdentitiesOnly=yes -o BatchMode=yes -o UserKnownHostsFile=/opt/cociber-secrets/known_hosts -o StrictHostKeyChecking=yes labops@10.10.30.12 'id -un'
```

Esperado: `labops`, sin solicitar contraseña. Repite el mismo comando cambiando solo el destino por SRVWEB y cada Kali preparada. Al finalizar:

```bash
sudo rm -f /run/cociber-labops-prueba
```

Si falla, revisa en la VM `sudo journalctl -u ssh.service --since '10 minutes ago' --no-pager`, la cuenta y sus permisos. No publiques claves ni registros con secretos. Conserva las integraciones deshabilitadas hasta resolverlo.

Siguiente: [03. LNXVICT](03_LNXVICT_SSH.md).
