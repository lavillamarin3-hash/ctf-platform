# CoCiber CTF · Guía práctica para crear grupos, laboratorios y retos

**Destinatarios:** administradores e instructores que preparan una demostración del cyber range.  
**Actualización:** 28 de octubre de 2026 · **Repositorio:** `lavillamarin3-hash/ctf-platform`  
**Importante:** esta guía describe los campos reales de CoCiber CTF; no sustituye la configuración de las máquinas Nutanix ni inventa credenciales. Los ejercicios deben probarse y las VMs verificarse antes de publicar.

## 0. Orden recomendado

1. Iniciar sesión con una cuenta **administradora**.
2. Crear/confirmar las **conexiones SSH/RDP en Guacamole**.
3. Crear los **laboratorios** y sus **máquinas virtuales**.
4. Crear **usuarios estudiantes** (rol `player`) y un **grupo**.
5. Vincular las VMs y conexiones y comprobar que se puede acceder realmente.
6. Crear los **retos** con sus banderas, asignarlos al grupo y publicar **solo tras la prueba piloto**.

**Red correcta:** atacantes = VLAN 20, `10.10.20.0/24`; víctimas = VLAN 30, `10.10.30.0/24`.

## 1. Inventario real de Nutanix AHV

| Rol | Nombre exacto de la MV | IP | Red |
|---|---|---|---|
| Atacante | LAB-KALI | 10.10.20.10 | VLAN 20 |
| Atacante | LAB-KALI-PURPLE | 10.10.20.11 | VLAN 20 |
| Atacante | LAB-KALI-BLUE | 10.10.20.12 | VLAN 20 |
| Víctima | LAB-WINVICT-A | 10.10.30.10 | VLAN 30 |
| Víctima | LAB-WINVICT-B | 10.10.30.11 | VLAN 30 |
| Víctima | LAB-LNXVICT | 10.10.30.12 | VLAN 30 |
| Víctima | LAB-SRVWEB | 10.10.30.20 | VLAN 30 |
| Víctima | LAB-SRVFSAD | 10.10.30.21 | VLAN 30 |

Las VMs ya instaladas en AHV **no se crean físicamente** al registrarlas en CoCiber: el formulario solamente registra su ficha de inventario. Evitar duplicar fichas existentes.

## 2. Administrar > Guacamole > Nueva conexión

Ejemplo de una conexión SSH de laboratorio:

| Campo de la pantalla | Qué ingresar |
|---|---|
| Nombre de conexión | `LAB-KALI - SSH` |
| Protocolo | `SSH` |
| Host / IP | `10.10.20.10` |
| Puerto | `22` (comprobar realmente) |
| Usuario o hostname de la máquina virtual | El **usuario SSH de esa VM** otorgado por infraestructura |
| Contraseña de la MV | La credencial entregada por infraestructura (no escribirla en un manual) |
| Grupo padre | `ROOT`, salvo organización explícita de Guacamole |

Para RDP de `LAB-WINVICT-A`, usar **RDP**, IP `10.10.30.10`, puerto `3389`, usuario y contraseña autorizados y dominio solo si aplica. El botón de **ojo**, dentro del campo contraseña, permite comprobar lo escrito. Al editar, deja contraseña vacía para conservar la existente; por seguridad la API no la devuelve.

**Verificar conexión** prueba primero un puerto desde la API y abre el portal de Guacamole. Aún debes **iniciar sesión realmente** y comprobar que la terminal o escritorio funciona antes de marcar la VM como disponible. Comprobar permisos y ACL entre VLAN.

## 3. Administración > Laboratorios / VMs > Nuevo laboratorio

Crear **dos laboratorios distintos**:

| Campo | Laboratorio de atacantes | Laboratorio de víctimas |
|---|---|---|
| Código | `LAB-ATACANTES` | `LAB-VICTIMAS` |
| Nombre | Laboratorio de Atacantes | Laboratorio de Víctimas |
| Descripción | Máquinas Kali autorizadas para ejercicios de ataque controlado | Máquinas objetivo aisladas para pruebas de seguridad |
| Estado | **Planificado** hasta verificar | **Planificado** hasta verificar |
| Entorno / segmento | `VLAN 20 · 10.10.20.0/24 · Nutanix AHV` | `VLAN 30 · 10.10.30.0/24 · Nutanix AHV` |

Si ya existen con esos códigos, elige **Editar**, no **Nuevo**. Guardar y pulsar **Actualizar inventario** para verificar que los datos persisten.

### Agregar MV en cada laboratorio

Ejemplo **Kali**:

| Campo | Valor |
|---|---|
| Nombre de VM | `LAB-KALI` |
| Sistema operativo | Kali Linux (la opción equivalente disponible) |
| Rol de red | Atacantes |
| Dirección IP | `10.10.20.10` |
| VLAN / subred | `VLAN 20` / `10.10.20.0/24` |
| Perfil | Standard / Atacante, según opciones del formulario |
| Estado | `planned` hasta probar |
| Conexión Guacamole | La conexión SSH/RDP registrada para **esta misma VM** |

Para **LAB-LNXVICT**, usar `Víctimas`, `10.10.30.12`, VLAN 30 y su conexión SSH. Para **LAB-SRVWEB**, usar `10.10.30.20`, VLAN 30; dentro de ella están los servicios web de práctica.

**No publiques contraseñas ni enlaces con tokens** en el campo descripción. Cuando la API rechaza el guardado, el formulario debe mantenerse abierto y mostrar el error; no asumas que se guardó hasta comprobar el listado tras recargar.

## 4. Administración > Usuarios > Nuevo usuario

| Campo | Valor de ejemplo |
|---|---|
| Usuario | `estudiante_demo01` |
| Nombre completo | Estudiante de demostración |
| Contraseña | Una contraseña individual, segura, no incluida en este documento |
| Rol | **player / Estudiante** |
| Función | Estudiante |
| Estado | Activo |

El botón de ojo queda **dentro de la entrada de contraseña**. Los usuarios estudiantes deben tener una cuenta individual: evita compartir una única cuenta con varios participantes.

## 5. Administración > Grupos de estudiantes > Nuevo grupo

Rellenar:

| Campo | Ejemplo |
|---|---|
| Nombre | Grupo piloto de ciberseguridad |
| Código | `GRP-PILOTO-01` |
| Descripción | Grupo autorizado para pruebas de SSH, web y DVWA |

Pulsar **Crear grupo**. La plataforma necesita tanto el registro PostgreSQL como el grupo correspondiente en Guacamole. Después seleccionar el grupo, agregar estudiantes activos y **asignar retos**.

**Error conocido de versiones anteriores:** `POST /api/v1/groups` respondía **HTTP 405** porque faltaba registrar la ruta en FastAPI. El código de `main` ya incluye el decorador. Si vuelve a aparecer **405**, la instancia API desplegada probablemente no está actualizada: confirmar despliegue de backend y recargar la página. El mensaje de Chrome *LanguageDetector* es informativo, no causa el 405.

Si aparece **409**, revisar que no exista otro código/nombre igual en PostgreSQL o Guacamole. Si aparece **502**, comprobar conectividad y permisos de la cuenta de servicio de Guacamole: la creación requiere su API.

## 6. Administración > Retos > Nuevo reto

### Qué significa cada sección

| Sección | ¿Obligatoria? | Uso |
|---|---|---|
| **1. Datos generales y activo principal** | Sí | Código, nombre, categoría, dificultad, VM o URL, puntos, descripción |
| **Escenario y técnica MITRE** | Opcional | Identificar el tipo de ejercicio para que la API aplique la estrategia correcta |
| **2. Instrucciones** | Opcional | Texto que verá el estudiante |
| **3. Pistas** | Opcional | Hasta 3 pistas; cada una puede descontar puntos |
| **4. Temporizador académico** | Opcional e independiente | Duración y porcentaje de puntuación tras el plazo |
| **5. Recursos educativos** | Opcional | Videos y presentaciones |
| **6. Banderas** | Necesario para completar retos con evidencia | Tipo estático/dinámico, etiqueta, orden |
| **7. Asignación a grupos** | Necesario para que el estudiante vea el reto | Grupo piloto u otro |

**Importante:** desactivar el temporizador **no da acceso ilimitado a una VM**: el backend mantiene un TTL técnico para liberar recursos. No se muestra el reloj ni se descuenta puntuación por vencimiento académico, pero la sesión remota puede cerrarse al llegar a su límite de seguridad. Desactivar pistas evita exigir campos de pistas vacías.

### Reto A — Fuerza bruta SSH de práctica

| Campo | Valor |
|---|---|
| Código | `ESC-02-BRUTEFORCE` |
| Nombre | Fuerza bruta de credenciales SSH — cuenta temporal |
| Categoría | `REDES` o `SSH` |
| Dificultad | **Medio** |
| Escenario | `SSH-PASSWORD-LAB` |
| MITRE | `T1110.001 — Password Guessing` |
| Laboratorio / VM principal | `LAB-KALI` |
| Activos adicionales | `LAB-LNXVICT` |
| Puntos | **250** |
| Descripción | Probar únicamente 12 candidatas sobre una cuenta SSH temporal del servicio didáctico |
| Instrucciones | Iniciar en Kali, abrir el reto, consultar el usuario temporal y el diccionario de práctica; recuperar y enviar la bandera desde el servicio de laboratorio |
| Flag | **Una flag dinámica activa**, por ejemplo plantilla `FLAG{ssh_practice_{{RAND}}}` |
| Grupo | `GRP-PILOTO-01` |

**Servicio objetivo:** `LAB-LNXVICT 10.10.30.12:2222` — **NO** el SSH administrativo del puerto 22. La estrategia debe poder preparar la cuenta temporal desde backend. No escribir una flag manual fija: se genera por corrida.

### Reto B — Aplicación web Operación Cóndor

| Campo | Valor |
|---|---|
| Código | `WEB-CONDOR` |
| Nombre | Operación Cóndor: auditoría del centro de mando |
| Categoría | `WEB` |
| Dificultad | **Medio** |
| Escenario | `CONDOR-WEB-LAB` |
| Técnica MITRE | `T1110.001 — Password Guessing` |
| Portal externo | URL **real** de Operación Cóndor en `LAB-SRVWEB` — verificar host/puerto antes de guardarla |
| Terminal Kali | Activar si se requiere investigación desde `LAB-KALI` |
| Puntos | **250** |
| Descripción | Investigar cuentas de práctica, comprobar credenciales autorizadas y publicar un comunicado de auditoría |
| Tipo de flag | **Estática**, con el **valor real** entregado por el portal en el laboratorio |
| Grupo | `GRP-PILOTO-01` |

**No confundir** esta bandera con DVWA. En la integración actual de Operación Cóndor la bandera es compartida por instalación; no es correcto anunciarla como dinámica por estudiante hasta implementar su aislamiento. Al editar el portal externo hay que conservar el prefijo interno `CONDOR-PORTAL:` que genera el formulario.

### Reto C — Explotación SQL en DVWA

| Campo | Valor |
|---|---|
| Código | `ESC-03-WEBEXPLOIT` |
| Nombre | DVWA: extracción de evidencia SQL de la corrida |
| Categoría | `WEB` |
| Dificultad | **Medio** |
| Escenario | `DVWA-SQLI-LAB` |
| Técnica MITRE | `T1190 — Exploit Public-Facing Application` |
| Laboratorio / VM principal | `LAB-KALI` |
| Activos adicionales | **Solo** `LAB-SRVWEB` |
| Puntos | **250** |
| Descripción | Identificar la fila de evidencia asignada a la corrida, dentro de `ctf_app_db.secrets`, mediante SQL Injection de DVWA |
| Instrucciones | Abrir desde Kali `http://10.10.30.20/dvwa/`, usar el módulo SQL Injection del entorno autorizado, recuperar la flag de la fila asignada y enviarla |
| Tipo de flag | **Una flag dinámica activa**, plantilla `FLAG{dvwa_sql_{{RAND}}}` |
| Grupo | `GRP-PILOTO-01` |

**Recomendado:** usar el configurador seguro `configure_dvwa_catalog.py`, que prepara el catálogo solo si existe el grupo y protege configuraciones incompatibles. El reto exige servicio auxiliar `labops` e inyección en MariaDB aprobados; `DVWA_LAB_ENABLED=false` por defecto. No publicarlo hasta completar la prueba piloto.

## 7. Tiempo y pistas: ejemplos

**Ejemplo A: reto introductorio guiado**
- Instrucciones: **activadas**.
- Pistas: **activadas** (1 o 2 pistas completas con título, explicación y descuento).
- Temporizador: **activado**, por ejemplo 60 minutos, 25 % de puntos al expirar.
- Recurso educativo: opcional.

**Ejemplo B: práctica libre supervisada**
- Instrucciones: activadas.
- Pistas: desactivadas.
- Temporizador: desactivado.
- El reto **sigue cerrando la reserva técnica** al vencer el TTL interno configurado para proteger la infraestructura.
- Flag: activa si debe otorgar puntos por evidencia.

Al editar un reto existente, las secciones opcionales que se deshabiliten no exigen sus campos; el formulario conserva las instrucciones o recursos ya guardados cuando se encuentran desactivados. La política nueva no debe alterar puntos ya otorgados ni corridas activas.

## 8. Lista de verificación antes de demostrar

1. Abrir **Usuarios**, crear un estudiante de prueba y entrar con esa cuenta.
2. Abrir **Grupos**, confirmar `GRP-PILOTO-01`, asignar el estudiante y el reto.
3. Abrir **Laboratorios**, comprobar IP y conexión Guacamole correcta.
4. Usar **Verificar conexión** y confirmar manualmente una sesión SSH/RDP real.
5. Crear/editar un reto, guardar y **recargar** para confirmar todos los campos persistidos.
6. Alternar claro/oscuro: comprobar contraste, campos completos y ningún control superpuesto.
7. Iniciar una corrida con el estudiante, recuperar bandera y enviarla.
8. Comprobar ranking y que cerrar la corrida limpia recursos temporales.
9. Repetir con un segundo estudiante; comprobar independencia de flags SSH/DVWA.
10. Revisar **GitHub Actions** del commit desplegado: frontend compilado y backend probado. Los tests no sustituyen la prueba real de Nutanix.

### Si el grupo sigue respondiendo 405 después del merge a main

En el host de aplicación, **tras respaldo y siguiendo la ventana de mantenimiento**, verificar:

```bash
git status --short
git log -1 --oneline
git fetch origin
git pull --ff-only origin main
sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml build api
sudo docker compose -f docker-compose.prod.yml up -d --no-deps api
sudo docker compose -f docker-compose.prod.yml ps
```

El navegador debe conectarse a la API actualizada, no a una instancia vieja detrás de un proxy. **No usar `docker compose down -v`**, no cambiar la base de datos de Guacamole y no publicar contraseñas.

Consulta también `Docs/VALIDACION_UIUX_GUACAMOLE_SESIONES_20261028.md` y `Docs/NUTANIX_DVWA_LAB_SRVWEB_IMPLEMENTACION.md`.
