# CoCiber CTF · Guía de validación UI/UX y sesiones (28-10-2026)

**Alcance:** frontend React, backend FastAPI y Guacamole 1.6.0 existentes. No modifica Nutanix, Netplan, firewall, Guacamole Docker ni las bases de datos. Código integrado en `main`, **despliegue y validación de infraestructura por realizar**.

## 1. Guacamole: dos URL distintas

| Variable | Uso | Valor documentado del laboratorio |
|---|---|---|
| `GUACAMOLE_API_URL` | Backend CoCiber `10.10.10.13` → API Guacamole por red de administración | `http://10.10.10.10:8080/guacamole` |
| `GUACAMOLE_BASE_URL` | Portal desde el navegador del usuario | `http://10.195.20.22:8080/guacamole` |

**Nunca copies credenciales reales en Git.** Verifica que el navegador tiene acceso a `10.195.20.22` y la API al host interno. La cuenta `ctf_guac_service` es una propuesta y debe existir realmente con permisos mínimos antes de utilizarla.

En Administración > Guacamole > Nueva conexión verifica:

1. El campo **Usuario o hostname de la máquina virtual** permite escribir y guardar el usuario SSH/RDP; no es la dirección IP (esta se introduce en **Host / IP**).
2. **Contraseña de la MV** incluye ojo mostrar/ocultar. Al **editar**, el campo se presenta vacío porque el backend nunca devuelve contraseñas: al dejarlo vacío se conserva la contraseña anterior. Para modificarla hay que introducir una nueva.
3. Cambiar **SSH → RDP** ajusta el puerto a 3389 y muestra **Dominio (RDP)**; cambiar de vuelta a SSH ajusta a 22 y elimina parámetros exclusivos de RDP.
4. El botón **Verificar conexión** abre en otra pestaña **solo** el portal con `GUACAMOLE_BASE_URL` y ejecuta además un preflight TCP desde API. **Abrir el portal o ver un puerto abierto no valida credenciales remotas ni habilita automáticamente la VM**.
5. Si se guarda con datos inválidos, comprobar que el formulario no se cierra y el error aparece. Recargar el listado y comprobar persistencia real.

## 2. Login, control de sesiones y cierre

El login tiene icono de ojo. El frontend intenta detectar pestañas duplicadas que copiaron `sessionStorage` mediante `BroadcastChannel`. La garantía principal contra un **segundo login** es la reserva en Redis **solo cuando se habilita**:

```dotenv
SINGLE_SESSION_ENABLED=false
```

Esta opción permanece **desactivada por defecto**. Probar primero en un piloto y cambiarla a `true` únicamente tras confirmar que Redis funciona, los estudiantes cerraron sesiones anteriores, y el tiempo de acceso `ACCESS_TOKEN_MINUTES` es apropiado (20 por defecto). Una sesión que no se cierre queda reservada hasta que expire el TTL; no elimina registros de retos ni flags. Al cerrar sesión se elimina la reserva propia mediante comparación atómica. **No fuerza la desconexión de otras pestañas que estén utilizando exactamente el mismo token en todos los navegadores posibles**; la detección cliente es una medida adicional. Este cambio no garantiza exclusividad de un túnel remoto ya abierto.

Prueba manual:

1. Login de un estudiante en navegador A.
2. Si `SINGLE_SESSION_ENABLED=true`, intenta iniciar con la misma cuenta desde B: debe responder HTTP 409 sin emitir otro token.
3. Ejecuta logout en A. Comprueba que B puede iniciar sesión.
4. En A, inicia sesión y duplica la pestaña: la copia debe cerrarse por evento de sesión expirada cuando el navegador admite `BroadcastChannel`.
5. Comprueba que un error de Redis **no permite** saltarse el control cuando está habilitado.

**La política es por cuenta de CoCiber CTF**, no reemplaza controles de concurrencia del laboratorio ni el límite real de conexiones del servidor Kali.

## 3. Laboratorios y modelo de red

- VLAN 20: Atacantes `10.10.20.0/24` (`10.10.20.10`, `.11`, `.12`).
- VLAN 30: Víctimas `10.10.30.0/24` (`10.10.30.10`, `.11`, `.12`, `.20`, `.21`).

**No utilizar `10.10.20.xx` como segmento de víctimas:** contradice el inventario AHV. Edita una VM, guarda y recarga. En fallo de backend la ventana debe permanecer abierta mostrando el motivo; en éxito debe mantenerse el dato almacenado en PostgreSQL. Compara la conexión de Guacamole relacionada y no cambies el estado a `ready` sin verificar una sesión real.

## 4. Retos: secciones habilitables

El editor tiene **Datos generales y activo principal** (obligatorios) y controles optativos para:

- Escenario / técnica MITRE.
- Instrucciones, tiempo y pistas.
- Videos y presentaciones.
- Banderas.
- Asignación a grupos.

Al desactivar una sección opcional, sus inputs se desmontan, por lo que dejan de exigir los campos de esa sección. Al editar un reto existente, los valores de secciones desactivadas **se conservan** (no se interpreta desactivar como eliminar datos existentes). Un reto nuevo sin flags o sin asignación a grupos se puede guardar, pero **no necesariamente ejecutar ni hacer visible a estudiantes**: configurar lo obligatorio antes de publicarlo para entrenamiento.

Prueba crear un borrador, editarlo, alternar cada sección, guardar y recargar. Si varias llamadas a la API crean datos parcialmente (reto, flags, grupos), inspeccionar cada sección tras recargar; esta secuencia **todavía no es una transacción distribuida atómica**.

## 5. Comprobaciones automáticas

GitHub Actions: `Validacion CoCiber CTF` ejecuta `node --test tests/*.cjs tests/*.mjs`, `npm run build` en frontend y `python -m unittest discover -s tests -p 'test_*.py'` en backend. Revisar resultado verde **del último commit de main**, no de commits anteriores.

**Queda pendiente verificar** con cuentas reales la apertura Guacamole, login SSH/RDP, actualización de PostgreSQL y sesiones concurrentes. No anunciar cierre completo de esa validación hasta ejecutarla sobre el despliegue de prueba.

## 6. Actualizar código en servidor de producción (sin levantar contenedores todavía)

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
sudo docker compose -f docker-compose.prod.yml config --quiet
```

Comprobar que no se altera el `.env` privado ni la BD de Guacamole. Seguir `GUIA_ACTUALIZAR_PRODUCCION.md` y respaldos antes de reconstruir contenedores. No usar `docker compose down -v`.
