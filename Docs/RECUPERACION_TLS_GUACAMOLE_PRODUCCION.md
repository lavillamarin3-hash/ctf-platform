# Recuperación segura de HTTPS, API y Guacamole en CoCiber CTF

**Objetivo:** resolver errores de Chrome `ERR_CERT_AUTHORITY_INVALID`, WebSocket `wss://10.195.20.21/api/v1/ws/ranking` y administración de Guacamole tras actualizar Git.  
**Principio:** no borrar usuarios, conexiones, IDs, permisos ni la base de datos propia de Guacamole. **La conexión a una VM ya registrada se consulta, no se recrea**.

## 1. Distinguir tres redes y tres servicios

| Elemento | Valor del proyecto | Acceso |
|---|---|---|
| App web + FastAPI | `10.10.10.13:8081` | Nginx frontend → API Docker `api:8000` |
| HTTPS visto por Chrome | `https://10.195.20.21` | Proxy inverso TLS (ubicación exacta por verificar) |
| Guacamole, API administrativa | `http://10.10.10.10:8080/guacamole` | Desde contenedor API, red administrativa |
| Guacamole, portal usuario | `http://10.195.20.22:8080/guacamole` | Desde navegador, red de estudiantes |
| PostgreSQL/Redis nativos | `10.10.10.14` | Solo backend de CoCiber |

Estas son **direcciones documentadas, no un diagnóstico en vivo**. Verificar el host, puerto y rutas reales; no copiar direcciones incorrectas a `.env`.

## 2. Prioridad 1: corregir el certificado HTTPS de la plataforma (10.195.20.21)

Cuando Chrome informa `net::ERR_CERT_AUTHORITY_INVALID` en **/api/v1/ranking, /api/v1/admin/guacamole/users y /connections**, rechaza TLS del **mismo origen web**, antes de que el navegador pueda completar esas peticiones. No es prueba de que la API Guacamole haya borrado las conexiones.

Desde un cliente Linux **con acceso a esa IP**:

```bash
curl --verbose https://10.195.20.21/api/v1/ranking
openssl s_client -connect 10.195.20.21:443 -showcerts </dev/null
openssl s_client -connect 10.195.20.21:443 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

Interpretación: revisar caducidad, cadena de certificados, CA emisora y **Subject Alternative Name (SAN)**. Si la navegación utiliza **IP**, el certificado debe tener SAN **IP:10.195.20.21**, no solo el nombre DNS. Cuando se utiliza un FQDN, este debe aparecer en SAN DNS y el navegador debe acceder por ese nombre. Para una CA corporativa, su certificado raíz/intermedio debe estar instalado de forma autorizada en los clientes y configurado en el servidor para entregar la cadena correcta.

En el **servidor que realmente termina TLS** (no necesariamente la VM de la aplicación):

```bash
sudo ss -tlnp | grep ':443'
sudo nginx -t
sudo nginx -T | grep -nE 'listen 443|ssl_certificate|proxy_pass|proxy_set_header Upgrade|server_name'
sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
```

Si el proxy TLS corre en Docker, revisar su propio volumen de certificados y configuración: el `nginx.conf` del frontend CoCiber solo escucha por **HTTP puerto 80** dentro del contenedor; **no controla el certificado de 10.195.20.21**. Renovar/instalar el certificado válido en el proxy TLS que corresponda, con copia de seguridad de la configuración, y recargar **únicamente** ese proxy tras `nginx -t`.

**NO** desactivar la verificación TLS en Chrome, `curl`, Python o Guacamole como solución permanente. **NO** guardar claves privadas ni certificados con claves en GitHub.

## 3. Prioridad 2: conservar las conexiones de Guacamole en su VM

En el servidor CoCiber **10.10.10.13**, revisar (sin imprimir ni publicar contraseñas):

```bash
git status --short
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml exec -T api python - <<'PY'
from app.core import get_settings
s = get_settings()
print("Modo:", s.guacamole_mode)
print("API interna:", s.guacamole_api_url)
print("Portal navegador:", s.guacamole_base_url)
print("Cuenta técnica configurada:", bool(s.guacamole_service_account))
print("Contraseña técnica configurada:", bool(s.guacamole_service_password))
PY
```

El `.env` privado y existente del backend debe conservar:

```dotenv
GUACAMOLE_MODE=real
GUACAMOLE_API_URL=http://10.10.10.10:8080/guacamole
GUACAMOLE_BASE_URL=http://10.195.20.22:8080/guacamole
GUACAMOLE_SERVICE_ACCOUNT=<cuenta-tecnica-real-existente>
GUACAMOLE_SERVICE_PASSWORD=<valor-privado-actual>
CTF_SEED_DEMO_DATA=false
MANAGE_SCHEMA_ON_STARTUP=false
```

**Valores de referencia, verificar con infraestructura.** No sustituir el `.env` existente por `.env.example`; no publicar su contenido completo.

Para consultar **sin crear ni borrar** conexiones reales:

```bash
sudo docker compose -f docker-compose.prod.yml exec -T api python - <<'PY'
import asyncio
from app.guacamole import make_guacamole_admin
async def main():
    adapter = make_guacamole_admin()
    print("Adaptador:", type(adapter).__name__)
    connections = await adapter.list_connections()
    print("Conexiones detectadas:", len(connections))
    for conn in connections:
        print(conn.identifier, conn.name, conn.protocol, conn.hostname, conn.port)
asyncio.run(main())
PY
```

Si aparece `StubGuacamoleAdapter`, el servidor está configurado en **modo demostración**, no consulta Guacamole real; corregirlo sin tocar la VM Guacamole. Si aparece `GuacamoleApiError` de red: comprobar desde el contenedor acceso a la IP administrativa y puerto 8080, además de la cuenta de servicio y permisos. No asumir que todas las conexiones se han perdido.

En el **backend actualizado** existe un endpoint exclusivo de administrador:

```http
GET /api/v1/admin/guacamole/inventory-audit
Authorization: Bearer <TOKEN_ADMIN>
```

Devuelve conteo de conexiones remotas, VM vinculadas, referencias de conexión que faltan y coincidencia de IP. **Solo lee**; no recrea conexiones, no borra credenciales ni actualiza IDs. Utilizar el panel de gestión de Guacamole para consultas normales y este endpoint si se necesitan verificar enlaces de inventario.

En la UI, si no se puede consultar Guacamole se muestra **«inventario no verificado»**, nunca «no existen conexiones»: evita reingresar registros que quizá ya estén presentes en la base de datos de Guacamole.

## 4. Prioridad 3: comprobar WebSocket del ranking

El frontend usa `wss://` automáticamente cuando el navegador está en `https://`. No hay que forzar `ws://`: sería contenido inseguro y fallaría. Primero corregir TLS; luego comprobar que el proxy inverso que termina TLS **permite Upgrade: websocket**.

La configuración del proxy TLS que redirige al frontend CoCiber debe tener, conceptualmente:

```nginx
# Ejemplo de los encabezados requeridos, NO reemplazar toda la configuración activa.
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto https;
proxy_read_timeout 3600s;
```

La configuración existente del Nginx web de CoCiber ya reenvía `/api/` a `api:8000` con Upgrade. El servidor TLS **adicional** también debe hacerlo. Si el handshake falla luego de validar el certificado, revisar el proxy, el ticket de sesión y los logs de la API.

El frontend ahora pausa reintentos cuando está oculto, desconectado o entra a Back-Forward Cache, y recupera la sesión cuando vuelve a estar visible. Eso reduce registros repetidos, **pero no sustituye la corrección del certificado**.

## 5. Actualización de Git sin destruir información

Desde el directorio del proyecto en `10.10.10.13`, después de respaldar archivos y verificar `git status`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml build api web
sudo docker compose -f docker-compose.prod.yml up -d --no-deps api web
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=80 api web
```

El despliegue afecta **solo a los contenedores web y API CoCiber**, no debe ejecutar comandos en LAB-GUAC ni borrar datos del PostgreSQL externo o de la base de datos Guacamole. **No ejecutar** `docker compose down -v`, `docker volume prune` ni recrear Guacamole por un error TLS.

## 6. Criterios de aceptación

1. Desde Chrome, abrir `https://10.195.20.21` **sin advertencia de certificado**.
2. `/api/v1/ranking` debe responder HTTP de aplicación (200/401, según autenticación), **no** error TLS.
3. El WebSocket `wss://10.195.20.21/api/v1/ws/ranking` establece conexión cuando el estudiante tiene sesión válida; no registra errores repetidos al navegar.
4. En Administración > Guacamole se muestran **las mismas conexiones reales** (identificador/nombre/protocolo) que antes de actualizar CoCiber.
5. La auditoría indica cero conexiones de VMs faltantes; revisar individualmente los enlaces que no coincidan, sin duplicar IDs.
6. Verificar en Guacamole las sesiones reales SSH/RDP. La comprobación de puerto no equivale a autenticación.
7. Los grupos, usuarios, retos y rankings siguen presentes tras actualizar.

**Si el TLS sigue rechazado por Chrome, no evaluar como falla de Guacamole el vacío de la UI:** las solicitudes ni siquiera han sido aceptadas por el origen HTTPS.
