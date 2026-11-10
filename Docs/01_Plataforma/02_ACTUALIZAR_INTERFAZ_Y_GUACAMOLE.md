# 02. Actualizar la interfaz y el módulo Guacamole de la instalación nueva

**Antes:** completa [01. Verificar la plataforma](01_VERIFICAR_PLATAFORMA_EXISTENTE.md). Si esta actualización visual ya está aplicada, revisa sus comprobaciones y pasa a [03. Guacamole](03_GUACAMOLE_Y_CONEXIONES.md) sin reconstruir otra vez.

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

En LAB-CTFWEB, antes de cualquier comando de esta guía:

```bash
cd /ctf-plataform/ || exit 1
pwd
```

Fecha: **9 de noviembre de 2026**. Punto de partida confirmado por el operador: plataforma nueva desplegada, conexión correcta a la BD y acceso con `admin_ctf`. Los laboratorios aún no están preparados.

Esta actualización modifica API y frontend. **No cambia el esquema ni requiere limpiar bases, cargar SQL, ejecutar init-db o crear otra vez admin_ctf.** Conserva `.env.fresh`, las credenciales, JWT_SECRET y los datos actuales.

## Cambios disponibles

- Login de dos paneles con el emblema de CoCiber, fondo azul oscuro, acentos violetas, tema claro/oscuro y botón para mostrar la contraseña.
- Menú lateral con iconos y nombres en español; panel derecho con perfil, resumen y pasos de preparación. Se puede ocultar para ampliar el contenido.
- Menú de usuario con cambio de tema, contraseña y cierre de sesión. El cambio obligatorio de contraseña inicial sigue vigente.
- Guacamole exclusivo para el rol **Administrador**: inventario remoto, búsqueda, filtro por protocolo, creación/edición/eliminación de conexiones SSH y RDP, y prueba de puerto.
- Listado y creación de cuentas remotas, consulta y asignación de permisos de apertura `READ` sobre conexiones permanentes del laboratorio. Conserva los demás permisos existentes; no modifica permisos globales de administradores de Guacamole.
- Formularios y tablas adaptados a móvil. La creación de una conexión requiere un nombre válido y una máquina seleccionada.

El módulo consulta Guacamole directamente; no requiere que ya existan laboratorios o retos. El selector de destinos utiliza el catálogo de VM confirmado del proyecto. **No crea VM, no concilia automáticamente las fichas de máquinas y no marca un laboratorio como disponible.**

## 1. Llevar el código actualizado al servidor

Los cambios de esta entrega están preparados en el repositorio local; no se hizo commit, push ni despliegue automático desde el chat. El responsable del código debe publicar primero la revisión aprobada en el remoto Git que utiliza este servidor. Después actualiza el checkout de `/ctf-plataform` con el procedimiento siguiente. No basta con reconstruir una copia que todavía tenga el código anterior.

Primero revisa, sin modificar nada:

```bash
git status --short
git branch --show-current
git remote -v
git rev-parse HEAD
```

Guarda el identificador de la revisión actual. Si hay cambios locales, detente y pide al responsable conservarlos/integrarlos; no ejecutes reset ni clean. Comprueba que la rama y el remoto sean los del despliegue. **Solo con la revisión deseada ya publicada y el checkout limpio**:

```bash
git pull --ff-only
```

Si no hay repositorio Git, falta acceso al remoto o el comando rechaza la actualización, el responsable debe transferir una revisión completa por el mecanismo de despliegue existente, conservando `.env.fresh`. No es necesario ni correcto crear otro clon vacío para continuar.

En el checkout actualizado deben existir:

```text
frontend/src/fresh/Layout.tsx
frontend/src/fresh/GuacamoleAdmin.tsx
backend/ctf/adapters/http/guacamole_admin.py
```

Conserva el archivo privado `.env.fresh` del servidor. No lo reemplaces por la plantilla ni copies `.env` histórico encima. Anota la revisión anterior para poder volver a ella.

## 2. Revisar la configuración privada de Guacamole

En LAB-CTFWEB:

```bash
cd /ctf-plataform
nano .env.fresh
```

Verifica estos campos con las credenciales existentes de **Guacamole**, distintas de las cuentas PostgreSQL/Redis y del administrador web:

```dotenv
GUACAMOLE_API_URL=http://10.10.10.10:8080/guacamole
GUACAMOLE_ADMIN_USER=USUARIO_TECNICO_EXISTENTE
GUACAMOLE_ADMIN_PASSWORD=CONTRASENA_EXISTENTE_DE_GUACAMOLE
GUACAMOLE_DATASOURCE=mysql
```

Los dos valores en mayúsculas son marcadores explicativos: escribe los valores privados reales solo en el servidor. Si tu URL y datasource reales son distintos, conserva los ya verificados. La cuenta técnica debe poder listar y administrar las conexiones y usuarios correspondientes; una respuesta vacía puede significar visibilidad insuficiente.

No se necesitan `SSH_INJECTOR_ENABLED=true` ni `DVWA_LAB_ENABLED=true` para consultar Guacamole. Mantén las integraciones de retos deshabilitadas hasta completar sus guías. No cambies `DATABASE_URL`, `REDIS_URL`, `PUBLIC_ORIGIN`, puertos ni proxy para esta mejora visual.

## 3. Actualizar API y web

Como todavía no has preparado laboratorios, comprueba que no existan corridas activas. Si hubiera alguna, ciérrala normalmente y espera su limpieza antes de actualizar. Si instalaste y activaste el worker, anota su estado y detenlo durante la sustitución; si no existe, omite ese paso.

```bash
sudo systemctl is-active cociber-fresh-worker.service
# Solo si estaba activo:
sudo systemctl stop cociber-fresh-worker.service
```

Verifica y construye las imágenes. Cada comando debe terminar correctamente antes de continuar:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml build api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml run --rm --no-deps api python -m ctf.infrastructure.cli check
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml up -d --force-recreate --wait --wait-timeout 180 api web
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
```

Solo si el worker estaba activo antes:

```bash
sudo systemctl start cociber-fresh-worker.service
sudo systemctl status cociber-fresh-worker.service --no-pager
```

La compilación del frontend usa `VITE_FRESH_INSTALL=true` desde este Compose. No mezcles `docker-compose.prod.yml` ni overlays históricos con este despliegue. No ejecutes `down -v`, reinstalación de bases o nueva creación del esquema.

## 4. Verificar desde el navegador

1. Recarga la página; si mantiene recursos antiguos, usa Ctrl+F5. Cierra sesión para comprobar el nuevo login y vuelve a entrar con `admin_ctf`.
2. Comprueba la paleta azul/violeta, el panel derecho y la opción de tema desde el menú de usuario.
3. Abre **Guacamole**. Pulsa **Actualizar inventario** y espera «API verificada» con la hora de consulta. Esto acredita la consulta HTTP, no la conectividad de cada VM.
4. Revisa nombres, protocolos, IP y sesiones. Las conexiones anteriores siguen en el servidor Guacamole; no se duplican automáticamente.
5. Pulsa **Probar puerto** en una conexión del laboratorio. El resultado verifica TCP desde la API. **No prueba la contraseña, la sesión SSH/RDP ni la ruta desde guacd.** Haz también la comprobación visual en el acceso Guacamole que ya utiliza tu instalación.
6. Para una conexión nueva, selecciona la VM, SSH o RDP y su puerto. Las opciones admitidas son SSH 22/2222 y RDP 3389 del catálogo controlado. Puedes dejar la contraseña vacía al editar para conservar la actual.
7. Para una cuenta remota nueva, crea el usuario y abre **Ver permisos** para asignarle las conexiones permanentes que podrá abrir. Crear esta cuenta no crea un jugador del CTF.

Las conexiones VNC o ajenas al catálogo se muestran en modo consulta. Las conexiones `ctf_*` de corrida y las que tienen sesiones activas no se pueden editar/eliminar desde este panel. La eliminación exige escribir el nombre exacto. La cuenta de servicio y los usuarios temporales de corrida están protegidos.

## 5. Continuar después con los laboratorios

El panel derecho presenta el siguiente paso según el inventario, los laboratorios disponibles y los retos publicados. No equivale a una certificación del estado real de las VM.

Continúa con [03. Guacamole y conexiones](03_GUACAMOLE_Y_CONEXIONES.md), después [04. Inventario y catálogo](04_INVENTARIO_Y_CATALOGO.md) y finalmente la [preparación de laboratorios](../02_Laboratorios/01_REQUISITOS_Y_TRANSFERENCIA.md). Los botones de piloto/publicación permanecen bloqueados si la estrategia está deshabilitada. ESC-01, ESC-04 y ESC-05 conservan su estado pendiente para otra fase.

## Diagnóstico y vuelta a la revisión anterior

| Síntoma | Revisar |
| --- | --- |
| No aparece Guacamole | Sesión con rol Administrador, revisión actualizada y compilación fresh de API/web |
| «No se pudo completar la operación en Guacamole» | URL privada, datasource, credenciales y permisos de la cuenta técnica; comunicación 10.10.10.13 → 10.10.10.10 |
| Inventario vacío | Visibilidad de la cuenta técnica en el datasource; no crear duplicados antes de verificar |
| No se puede editar/eliminar | Sesiones abiertas, conexión automática de corrida o destino fuera del catálogo |
| Puerto accesible pero no abre sesión | Credenciales de la VM, protocolo y ruta desde guacd; la prueba TCP no cubre autenticación |
| Laboratorios siguen pendientes | Es esperado: esta actualización no instala helpers ni ejecuta pilotos |

Si necesitas revertir, vuelve al código/imagen de la revisión anterior y reconstruye/recrea API y web con el mismo Compose y `.env.fresh`. No requiere restaurar la base por cambios de esquema, porque no los hay. Los cambios administrativos que hayas hecho en Guacamole sí persisten en ese servidor; volver al código anterior no los deshace.

## Validación de esta entrega

- Backend: 370 pruebas ejecutadas, 369 correctas y una omitida; incluye 13 pruebas nuevas del módulo Guacamole con adaptador simulado.
- Frontend: 40 pruebas existentes y tres nuevas de sesión correctas. La nueva prueba evita que una respuesta tardía de una sesión vencida cierre una sesión posterior.
- Compilación de la variante nueva correcta; revisión visual con datos simulados en escritorio y móvil, temas claro/oscuro, selección RDP y validación de formulario.
- Credenciales y parámetros secretos excluidos del inventario; destinos administrativos o externos rechazados por el backend; permisos de roles y conexiones protegidas comprobados.
- Sin ejecución en Guacamole real ni cambios en servidores desde esta entrega. La aceptación real corresponde a los pasos anteriores.
