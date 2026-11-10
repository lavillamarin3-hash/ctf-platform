# 06. Probar la inyección y activar el proceso de corridas

**Antes:** inventario conciliado, claves verificadas, helpers y permisos instalados en la víctima y en al menos una Kali. Completa [03](03_LNXVICT_SSH.md) y [04](04_KALI_SESIONES.md) para ESC-02; añade [05](05_SRVWEB_DVWA.md) para ESC-03. No debe haber corridas vivas en las máquinas que probarás.

## 1. Acceder a LAB-CTFWEB y revisar la configuración

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

En LAB-CTFWEB:

```bash
cd /ctf-plataform/ || exit 1
sudo stat -c '%U:%G %a %n' /opt/cociber-secrets /opt/cociber-secrets/labops_ed25519 /opt/cociber-secrets/known_hosts
nano .env.fresh
```

Conserva las conexiones y contraseñas que ya funcionan. Revisa estas variables; no contienen una flag fija:

```dotenv
SSH_INJECTOR_USER=labops
SSH_INJECTOR_KEY_PATH=/run/secrets/labops_ed25519
SSH_INJECTOR_KNOWN_HOSTS=/run/secrets/known_hosts
SSH_INJECTOR_ENABLED=false
DVWA_LAB_ENABLED=false
WINRM_INJECTOR_ENABLED=false
```

`/run/secrets` es la ruta **dentro del contenedor**; corresponde a `/opt/cociber-secrets` del servidor. No la cambies por `/ctf-plataform`. El directorio debe permitir acceso al grupo 10001 y los archivos privados deben ser legibles por ese grupo, conforme a [02](02_CUENTA_TECNICA_Y_CLAVES.md).

Guarda con Ctrl+O, Enter y Ctrl+X. Comprueba la configuración sin imprimir secretos:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli check
```

Esperado: sin error de Compose y `PostgreSQL y Redis: OK`.

## 2. Probar cada víctima preparada

Para ESC-02:

```bash
sudo bash scripts/probar_inyector.sh LAB-LNXVICT SSH-PASSWORD-LAB
```

Solo si preparaste también ESC-03:

```bash
sudo bash scripts/probar_inyector.sh LAB-SRVWEB DVWA-SQLI-LAB
```

Cada comando genera una evidencia de prueba, ejecuta `create → check → destroy` y no imprime la bandera. El diagnóstico habilita internamente la prueba sin activar globalmente el escenario. Resultado esperado: `create → check → destroy: OK`. La máquina queda **en mantenimiento**, incluso cuando la prueba pasa. Esta prueba no crea una sesión en Kali ni comprueba el navegador de DVWA; eso se revisa en el piloto y la demo.

Si falla, no marques la VM disponible. Revisa la clave/known_hosts de [02](02_CUENTA_TECNICA_Y_CLAVES.md), el permiso sudo y la compilación del helper de la víctima. Si el comando informa corridas vivas, solicita su cierre normal y espera a que se liberen. No borres reservas en SQL para continuar.

## 3. Activar exclusivamente los escenarios comprobados

```bash
nano .env.fresh
```

Después de aprobar ESC-02 establece `SSH_INJECTOR_ENABLED=true`. Después de aprobar también ESC-03 establece `DVWA_LAB_ENABLED=true`; de lo contrario conserva `false`. `WINRM_INJECTOR_ENABLED` sigue `false`. Las banderas se generan por corrida; no se rellenan variables de flags estáticas del sistema anterior.

Si el worker ya existe y está activo, deténlo antes de recrear los servicios:

```bash
sudo systemctl is-active cociber-fresh-worker.service
```

Solo si responde `active`:

```bash
sudo systemctl stop cociber-fresh-worker.service
```

Valida y aplica:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml up -d --force-recreate --wait --wait-timeout 180 api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
```

## 4. Instalar el worker supervisado

El worker procesa la cola y la limpieza. La API funcionando por sí sola no basta. Revisa la unidad incluida:

```bash
grep '^WorkingDirectory=' deploy/systemd/cociber-fresh-worker.service
command -v docker
```

Debe mostrar `WorkingDirectory=/ctf-plataform` y Docker en `/usr/bin/docker`. Si la instalación usa otra ruta del ejecutable, el administrador debe ajustar ExecStart/ExecStop antes de instalar. Con esas comprobaciones correctas:

```bash
sudo install -o root -g root -m 0644 deploy/systemd/cociber-fresh-worker.service /etc/systemd/system/cociber-fresh-worker.service
sudo systemctl daemon-reload
sudo systemctl enable --now cociber-fresh-worker.service
sudo systemctl status cociber-fresh-worker.service --no-pager
sudo journalctl -u cociber-fresh-worker.service -n 40 --no-pager
```

Esperado: unidad `active (running)`, sin reinicios continuos ni errores de conexión. No inicies otro worker manual mientras esta unidad esté activa.

## 5. Confirmar las fichas desde la web

1. Entra como administrador y abre **Máquinas**.
2. En una preparación inicial, sin registro de restauración pendiente y con las pruebas anteriores aprobadas, pulsa **Disponible** en la víctima y las Kali preparadas.
3. Si existe un registro pendiente, ve a **Mantenimiento** y pulsa **Confirmar restauración probada**, después de completar la restauración real y su prueba. No uses la edición de estado para eludir este registro.
4. Deja las demás máquinas en «Por preparar». En **Laboratorios**, confirma disponibles `LAB-ATACANTES` y `LAB-VICTIMAS` cuando cada uno tenga al menos una máquina preparada.

Siguiente: [07. Grupos, retos y piloto](07_GRUPOS_RETOS_Y_PILOTO.md).
