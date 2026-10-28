# CoCiber CTF · SSH dinámico con Kali Blue y acceso SSH/RDP del estudiante

**Fecha:** 28-10-2026. **Objetivo:** corregir los errores al iniciar `ESC-02-BRUTEFORCE` sin inyectar banderas en Kali y sin duplicar conexiones Guacamole.

## 1. Topología correcta

| Nombre | IP | Función | Puerto |
|---|---|---|---|
| `LAB-KALI-BLUE` | `10.10.20.12` | Atacante del estudiante | SSH 22 y, **solo si está instalado**, RDP 3389 |
| `LAB-LNXVICT` | `10.10.30.12` | Víctima donde el backend crea una cuenta SSH temporal y flag | SSH administrativo 22 para API; servicio de práctica 2222 para Kali |
| `LAB-GUAC` | `10.10.10.10:8080/guacamole` | Almacén independiente de conexiones y permisos SSH/RDP | API Guacamole |
| `LAB-CTFWEB` | `10.10.10.13` | FastAPI y frontend Docker | Contenedores `api` y `web` |

**Nota:** `LAB-KALI-LBUE` es un error de escritura: el identificador de inventario correcto es **`LAB-KALI-BLUE`**. No crear otra VM para corregir esa diferencia. No publicar usuarios/contraseñas del sistema en la descripción del reto.

**El estudiante se conecta por SSH o RDP a Kali Blue.** Desde Kali se conecta al **servicio SSH didáctico 2222** de LAB-LNXVICT y recupera `flag.txt`. RDP **no** se habilita automáticamente instalando CoCiber; requiere un servicio remoto realmente activo en Kali.

## 2. Preflight antes de crear o editar

En administración de CoCiber:

- **Laboratorios:** una ficha `LAB-LNXVICT` con IP `10.10.30.12`, Linux/Ubuntu y estado `ready`; una ficha `LAB-KALI-BLUE` con IP `10.10.20.12`, Kali Linux y estado `ready`. Sus laboratorios también deben figurar `ready`. Comprobar primero las VMs.
- **Guacamole:** verificar por sesión real las conexiones existentes a `10.10.20.12`: **SSH 22** y, si el servicio está activo, **RDP 3389**. Para cada protocolo debe existir exactamente una conexión por IP, no duplicados. La cuenta estudiante debe tener permiso **READ** en las conexiones elegidas. El grupo también puede recibir permisos al sincronizarse desde CoCiber.
- **Grupos:** seleccionar un grupo existente, activo y con al menos un usuario estudiante.
- **Backend:** desde `10.10.10.13` comprobar el inyector y la cuenta técnica de LAB-LNXVICT mediante `python -m app.check_flag_injector`. No pegar contraseñas ni claves en la consola.

Si aparece `No fue posible conectar con la API`, revisar primero TLS de **`https://10.195.20.21`** y los certificados del proxy web. Ese fallo es independiente del creador de retos.

## 3. Creación o reparación idempotente del reto en PostgreSQL

Usar **únicamente** `docker-compose.prod.yml` en el servidor web, dentro del clon Git `ctf-platform` actualizado.

### 3.1. Comprueba primero qué código está ejecutándose

```bash
git status --short
git log -1 --oneline
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml exec -T api python -m app.check_flag_injector
```

Si `git status` no está limpio, revisar los cambios antes de actualizar. Si el despliegue automático está habilitado, **no lo ejecutes simultáneamente de forma manual**.

### 3.2. Simulación sin modificar la base

Sustituye `GRP-PILOTO-01` por el **código real** del grupo de estudiantes existente:

```bash
sudo docker compose -f docker-compose.prod.yml exec -T api \
  python configure_ssh_access_challenge.py --group GRP-PILOTO-01 --attacker LAB-KALI-BLUE
```

La salida JSON indica si falta crear el reto, corregir su escenario, añadir una bandera dinámica o asignar el grupo. **No escribe nada** sin `--apply`.

Para continuar, debes ver que el reto, grupo y máquinas son coherentes. Si indica que hay corridas activas, ciérralas normalmente desde el usuario; no borres registros ni locks Redis manualmente.

### 3.3. Aplicar solamente tras respaldar PostgreSQL

```bash
sudo docker compose -f docker-compose.prod.yml exec -T api \
  python configure_ssh_access_challenge.py --group GRP-PILOTO-01 --attacker LAB-KALI-BLUE --apply
```

**No edita otros retos, no borra resultados, ni crea/borra conexiones SSH/RDP de Guacamole.**

- Reto nuevo: se crea en **borrador**, con bandera dinámica y grupo asignado.
- Reto existente: se corrigen únicamente escenario y activos, siempre que no tenga una corrida activa; se reutiliza la bandera dinámica válida ya registrada.
- Reto existente con una bandera estática activa o varias banderas activas: **se detiene y solicita revisión manual**, sin alterar sus valores.
- Reto eliminado intencionalmente: su recreación debe ser una decisión explícita del administrador y respaldarse.

### 3.4. Verificar el formulario de Gestión de Reto

En Administración > Retos > `ESC-02-BRUTEFORCE`:

| Campo | Valor |
|---|---|
| Código | `ESC-02-BRUTEFORCE` |
| Nombre | Práctica SSH: recuperación de bandera dinámica |
| Categoría | `REDES` |
| Dificultad | `Medio` |
| Escenario | `SSH-PASSWORD-LAB` **exactamente** |
| MITRE | `T1110.001 — Password Guessing` |
| Laboratorio / VM principal | **`LAB-LNXVICT`** (víctima) |
| Activos adicionales | **`LAB-KALI-BLUE`** (una Kali atacante) |
| Puntos | `250` |
| Bandera | **Una bandera dinámica activa** con plantilla no vacía |
| Asignación | Grupo existente activo con estudiante matriculado |
| Publicación | Solo después de verificar SSH/RDP y preflight de la VM |

La bandera final **no se escribe manualmente en el formulario**. Al iniciar la corrida, `ssh_practice.py` genera su evidencia única a partir de los identificadores de usuario y corrida.

**No mezclar** código `ESC-02-BRUTEFORCE` con escenarios genéricos: si falta `SSH-PASSWORD-LAB`, la API bloquea el inicio con un mensaje específico, en lugar de intentar inyectar en la máquina atacante.

## 4. Comprobar SSH y RDP reales en Kali Blue

Desde **LAB-KALI-BLUE**, revisar puertos de servicio local:

```bash
ip -br addr
sudo ss -lntp | grep -E ':(22|3389)\b' || true
systemctl is-active ssh || true
systemctl is-active xrdp || true
```

Si `xrdp` figura inactivo o no existe, **no anuncies RDP como disponible**. Debe instalarse/configurarse en una ventana autorizada y verificarse antes de dar acceso a estudiantes.

En Guacamole, **reutiliza conexiones existentes** que apunten a `10.10.20.12`. Si falta una, créala como administrador del Guacamole independiente, usando el protocolo correcto y usuario técnico autorizado **sin compartir credenciales del backend**. Comprueba el acceso desde el portal como estudiante. No crees duplicados ni borres conexiones.

En una corrida activa, el menú de la terminal mostrará solamente los protocolos que existan, sean únicos y tengan permiso READ para el estudiante. El usuario no podrá elegir manualmente la VM víctima desde el navegador.

## 5. Probar el reto como estudiante

1. Inicia sesión con una cuenta **player** que esté matriculada en el grupo seleccionado.
2. Abre Retos > **ESC-02-BRUTEFORCE** > **Iniciar reto**.
3. En **Laboratorio asignado**, abre la terminal de Kali Blue usando **SSH**. Cambia a **RDP** únicamente cuando se haya verificado la conexión.
4. La plataforma muestra **usuario temporal**, IP/puerto `10.10.30.12:2222` y un diccionario limitado a doce candidatas.
5. Desde Kali, investiga solamente `10.10.30.12:2222` usando las instrucciones del reto. Con la contraseña temporal identificada, abre una conexión SSH a ese puerto. El servicio no admite las cuentas administrativas de Linux.
6. Ejecuta `cat flag.txt` en la **shell didáctica** y copia el valor de bandera `FLAG{...}`.
7. Pégalo en el formulario **Enviar flag** de CoCiber, comprueba el puntaje y después pulsa **Cerrar laboratorio**.
8. Repite con otro estudiante para comprobar que no comparte la misma bandera.

Para comprobar desde Kali que el puerto de práctica está abierto **después de iniciar**:

```bash
nc -vz -w 3 10.10.30.12 2222
```

**Antes de iniciar una corrida el puerto 2222 puede estar cerrado por diseño**: el backend inicia el servicio restringido cuando provisiona una nueva cuenta.

## 6. Interpretación de errores

| Mensaje | Acción |
|---|---|
| No fue posible conectar con la API | Corregir certificado HTTPS y proxy web de `10.195.20.21` |
| El reto dinámico requiere VM víctima Linux | Revisar código `ESC-02-BRUTEFORCE` + escenario `SSH-PASSWORD-LAB` + víctima `LAB-LNXVICT` |
| VM Kali no disponible | Verificar nombre `LAB-KALI-BLUE`, IP `10.10.20.12`, registro único y laboratorio `ready` |
| SSH/RDP no autorizado | Verificar conexiones Guacamole únicas y permiso READ para la cuenta |
| No se pudo preparar SSH de práctica | Verificar preflight del inyector, SFTP, Paramiko en LNXVICT y sus servicios |
| Cuenta de práctica no existe | El reto todavía no inició, terminó o expiró; no usar credenciales reales del sistema |
| Otro estudiante ocupa una VM | No eliminar reservas activas; coordinar con instructor |

**Referencias internas:** `Docs/REPARAR_INYECCION_FLAGS_NUTANIX.md`, `Docs/RECUPERACION_TLS_GUACAMOLE_PRODUCCION.md`, `Docs/GUIA_FORMULARIOS_GRUPOS_LABS_RETOS_COCIBER.md`.
