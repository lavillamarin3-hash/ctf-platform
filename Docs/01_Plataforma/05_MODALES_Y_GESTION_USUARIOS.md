# 05. Actualizar los modales y la gestión de usuarios

Actualización del **10 de noviembre de 2026**, para la plataforma fresh ya operativa. Los cambios están en el repositorio local; deben transferirse al servidor antes de reconstruir. No se ha realizado un despliegue remoto desde esta entrega.

## 1. Acceder al proyecto existente

Desde PowerShell del equipo local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

Dentro de LAB-CTFWEB, como `lab-ctfweb`:

```bash
cd /home/lab-ctfweb/ctf-platform || exit 1
pwd -P
test -f .env.fresh && echo 'Configuración privada encontrada'
test -f deploy/docker-compose.fresh.yml && echo 'Compose fresh encontrado'
```

Esta es la ruta observada en las últimas sesiones del servidor. Las primeras guías utilizaban `/ctf-plataform`; no muevas el despliegue ni crees otra carpeta. Si la ruta difiere, localiza el checkout que realmente usa el servicio y confirma ambos archivos antes de continuar.

## 2. Transferir la revisión y conservar la configuración

El responsable del código debe publicar primero estos cambios en el remoto utilizado por el servidor. Revisa:

```bash
git status --short
git branch --show-current
git remote -v
git rev-parse HEAD
```

Guarda el identificador de la revisión anterior. Solo con el checkout limpio, rama correcta y revisión nueva ya publicada:

```bash
git pull --ff-only
```

Si hay modificaciones locales o no existe Git, conserva esos cambios y transfiere la revisión mediante el procedimiento existente. No uses `reset --hard`, `clean` ni sustituyas `.env.fresh`. Comprueba que llegaron los nuevos archivos:

```bash
test -f frontend/src/fresh/Modal.tsx && echo 'Modales presentes'
test -f frontend/src/fresh/UsersAdmin.tsx && echo 'Gestión de usuarios presente'
grep -n 'async def update_user\|async def delete_user' backend/ctf/adapters/http/routes.py
```

No hay cambios de esquema: **no ejecutar init-db, seed, bootstrap ni limpieza de BD** para esta actualización.

## 3. Preparar una ventana sin corridas

En la web, acuerda una pausa de nuevos inicios, cierra las corridas normalmente y espera su limpieza. Revisa también la cola. No actualices mientras existan corridas en cola, reservadas, activas o limpiándose. No detengas el worker antes de que termine esa limpieza.

En el servidor, verifica la configuración y construye primero:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml build api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli check
```

Cada comando debe terminar correctamente. Si falla alguno, corrígelo antes de sustituir contenedores. Conserva los valores de inyectores ya verificados para SSH/DVWA; esta mejora no exige deshabilitarlos ni cambiar secretos.

## 4. Actualizar API, web y worker

Comprueba el estado del worker y su directorio efectivo:

```bash
sudo systemctl is-active cociber-fresh-worker.service
sudo systemctl show cociber-fresh-worker.service -p WorkingDirectory -p ExecStart
```

`WorkingDirectory` debe coincidir con `pwd -P`. Conserva el ajuste local ya aplicado en `cociber-fresh-worker.service.d/10-project-directory.conf`; **no reinstales la unidad con la ruta antigua**. Si aún hay error `200/CHDIR`, corrígelo siguiendo [06. Pruebas y worker](../02_Laboratorios/06_PRUEBAS_Y_WORKER.md) antes de continuar.

Si el worker estaba activo, y las corridas ya están cerradas y limpias:

```bash
sudo systemctl stop cociber-fresh-worker.service
```

Recrea los servicios de la plataforma:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml up -d --force-recreate --wait --wait-timeout 180 api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
```

Solo si el comando terminó bien y el worker estaba activo antes, vuelve a iniciarlo:

```bash
sudo systemctl start cociber-fresh-worker.service
sudo systemctl status cociber-fresh-worker.service --no-pager
sudo journalctl -u cociber-fresh-worker.service -n 40 --no-pager
```

Si la actualización falla, mantén la pausa de nuevos inicios y consulta:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml logs --tail 80 api web
```

Para volver atrás, recupera la revisión/imagen anterior por el procedimiento habitual y reconstruye/recrea con el mismo Compose y configuración privada. No restaures la BD por un supuesto cambio de esquema: esta entrega no lo cambia. Los cambios de usuarios realizados después sí persistirán.

## 5. Usar la gestión de usuarios

Recarga con Ctrl+F5 e inicia sesión como `admin_ctf`. Abre **Usuarios**:

| Acción | Cómo usarla | Resultado |
| --- | --- | --- |
| Crear | «Nuevo usuario», nombre, rol y contraseña inicial de al menos 10 caracteres | Cuenta nueva; exige cambiar contraseña al entrar |
| Consultar | Buscar por nombre o rol | Lista con rol, estado y cambio de contraseña pendiente |
| Editar | «Editar» en una cuenta distinta del administrador | Cambiar nombre, rol o estado |
| Restablecer contraseña | En «Editar», completar la contraseña temporal | Invalida sesiones previas y exige cambiarla |
| Desactivar | «Editar» → Estado Inactivo | Impide acceso y conserva el historial |
| Eliminar | «Eliminar», escribir el nombre exacto | Elimina una cuenta sin historial; si tiene historial pide desactivarla |

Solo hay un administrador, protegido contra eliminación y cambio de rol/estado desde esta gestión. Su contraseña se cambia desde **Mi cuenta**. Los otros tres roles asignables son **Instructor, Jugador e Invitado**; el número de cuentas no está limitado a tres. Un instructor puede consultar usuarios, pero las modificaciones pertenecen al administrador.

Los cambios de cuenta invalidan las sesiones anteriores. Cuando un jugador pasa a otro rol, se retiran sus pertenencias a grupos; si vuelve a Jugador, hay que asignarlo de nuevo. Las cuentas con corridas en cola o sin limpiar no pueden modificarse ni eliminarse: cierra primero las corridas y espera al worker.

La eliminación no borra resultados ni auditoría en cascada. Una cuenta que ya inició sesión puede tener historial de auditoría aunque nunca haya completado un reto; usa Inactivo en ese caso.

## 6. Comprobaciones de aceptación

1. Crea una cuenta de prueba nueva sin reutilizar una existente. Comprueba que solo se ofrecen Instructor, Jugador e Invitado.
2. Antes de iniciar sesión con ella, cambia su rol entre esos tres valores y verifica el resultado al recargar la lista. Después puedes eliminarla escribiendo su nombre exacto, porque todavía no tiene historial propio.
3. Con otra cuenta de prueba, comprueba login, cambio obligatorio de contraseña, cambio de rol por el administrador e invalidación de la sesión previa. Desactívala al terminar para conservar la auditoría.
4. Confirma que `admin_ctf` aparece como «Cuenta protegida» y que un instructor no ve acciones de modificación de usuarios.
5. Abre los formularios de reto, grupo, laboratorio, asignación y Guacamole. Deben aparecer en una ventana modal, manteniendo visible el contexto de la página.
6. Cierra con Escape o «Cerrar»: el foco vuelve al botón de apertura. Mientras se guarda, no debe permitirse cerrar o enviar de nuevo. Los errores deben leerse dentro de la ventana.
7. Confirma que inventario, conexiones de Guacamole y el reto SSH previamente funcional siguen disponibles. La preparación de Windows/FTP empieza en [09](../02_Laboratorios/09_PREPARACION_WINDOWS_Y_FTP.md).

El login y el cambio obligatorio de contraseña inicial conservan su pantalla propia. Los formularios de gestión, cambio voluntario de contraseña y envío de bandera utilizan modales.

## Validación local de la entrega

Compilación fresh y 43 pruebas de frontend correctas; 27 pruebas unitarias fresh correctas. Los 15 casos de integración con PostgreSQL local comprobaron CRUD, permisos, protección del administrador, revocación de sesiones, conservación de historial y concurrencia con el inicio de corridas. La integración local utilizó PostgreSQL 18 y Python 3.11; la instalación objetivo usa PostgreSQL 16 y la imagen Python 3.12, por lo que corresponde completar esta aceptación en el servidor.

Revisión visual en navegador con datos simulados: edición de usuario, creación de conexión Guacamole y cierre por Escape con restitución de foco. No se han validado servicios Windows/FTP ni el despliegue en las VM desde este equipo.
