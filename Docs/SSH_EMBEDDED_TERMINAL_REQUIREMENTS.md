# Terminal integrada: implementación y operación

## Implementación

La terminal utiliza `Guacamole.Client` y `WebSocketTunnel`, no un iframe con `#/client/...`. La biblioteca oficial `guacamole-common-js/all.min.js` se obtiene desde la instalación configurada y se sirve en `/api/v1/terminal/client.js`, con caché por proceso. No incorpora credenciales.

El backend autentica la cuenta personal del estudiante al iniciar sesión CTF cuando ambas contraseñas coinciden. Si no puede hacerlo, la terminal solicita únicamente la contraseña personal de Guacamole mediante `/api/v1/terminal/auth`. La contraseña no se guarda; el token remoto queda cifrado con Fernet en Redis y expira con la sesión CTF. La clave se deriva del secreto HMAC existente, que debe ser privado y fuerte.

`POST /api/v1/runs/{id}/terminal/session` comprueba usuario, propiedad, estado, expiración, publicación, asignación a grupo activo y conexión de la instancia. Emite un ticket aleatorio de un uso, guardado por hash en Redis, en una cookie HttpOnly/SameSite=Strict de 60 segundos limitada a ese run. En HTTPS la cookie es Secure. El navegador no recibe el token de Guacamole, el destino remoto ni credenciales técnicas.

`/api/v1/runs/{id}/terminal/ws` valida Origin exacto, consume el ticket y conecta al túnel WebSocket real de Guacamole con la cuenta del estudiante. El destino se resuelve en backend; la query del navegador solamente permite dimensiones acotadas. No hay JWT en la URL. El ranking en vivo utiliza el mismo patrón de ticket, conservando el Observer original.

La conexión supervisa cada segundo el run y la sesión personal; cierra cuando se revoca, expira, pierde asignación o termina sesión. Una marca Redis distribuida bloquea nuevos túneles durante la limpieza, también entre workers. El cierre explícito desconecta los túneles locales antes de limpiar la VM y devolver la instancia. No termina globalmente otras conexiones a la misma VM. Los permisos READ temporales concedidos por una corrida se retiran; se conservan los preexistentes.

## Configuración necesaria

- Guacamole real y su conexión SSH preparados; cada estudiante debe existir allí.
- `GUACAMOLE_API_URL` (o `GUACAMOLE_BASE_URL`) accesible desde el contenedor API, incluyendo el contexto real, por ejemplo `/guacamole`. La API necesita acceder a `api/tokens`, la biblioteca pública y `websocket-tunnel`.
- `PUBLIC_ORIGIN` igual al origen visible del navegador (protocolo, host y puerto). No añadir slash final. No usar un origen comodín.
- HTTPS para producción. Si Guacamole y API atraviesan una red no confiable, usar HTTPS/WSS también entre ellos.
- Redis operativo, compartido por todos los workers y con acceso restringido. La misma clave HMAC debe existir en todos ellos.
- Proxy `/api/` con Upgrade WebSocket, HTTP/1.1, timeouts y buffering desactivado. La configuración Nginx incluida lo implementa; no requiere exponer `/guacamole/` en la SPA.
- Conservar la cuenta técnica y la del inyector exclusivamente en la configuración privada del servidor.
- No registrar URLs upstream con query completa: la API oficial de Guacamole utiliza tokens en sus solicitudes. Restringir y depurar también los logs del proxy/servidor Guacamole, no solo los de la plataforma.

## Experiencia y límites

La terminal se abre dentro del detalle del reto y también en la sección de laboratorio existente. Canvas redimensionable, teclado, ratón, foco, reconexión y escala de texto 100–200%, con 125% inicial. El portapapeles de texto recibido desde Guacamole aparece como selección que se puede preparar para enviar. El bloc es por corrida y pestaña; se elimina al cerrar o salir. El candidato también permite pegar directamente, sin transcribir ni validar flags en frontend. Si el navegador bloquea Clipboard API en HTTP, usar Ctrl+C/Ctrl+V sobre el campo.

La reutilización conserva el mismo run/flag; una nueva corrida genera su propia evidencia en backend. Si falla la limpieza, la ejecución permanece pendiente, conserva su reserva y permite reintentar; no presenta éxito falso.

La cuenta personal Guacamole cifrada dura como máximo la sesión CTF. Un token expirado remotamente puede exigir reconectar con la contraseña personal. La solución no modifica globalmente el proveedor SSO de Guacamole ni elimina permisos ajenos/preexistentes.

## Verificación

El cliente público y la autenticación administrativa de la instalación real respondieron durante la inspección. Un 302 del contexto raíz no prueba por sí mismo que sea un redireccionamiento de login. No se utiliza esa heurística ni se considera autenticado un enlace opaco.

Las pruebas unitarias validan autorización, tickets, cookies, límites y cleanup con dobles. La prueba de navegador utiliza la biblioteca oficial real con API/WebSocket de prueba, por lo que demuestra el comportamiento del cliente e interfaz, no una ejecución física SSH. Ver `VERIFICACION_RELEASE.md` para la aceptación pendiente en el entorno desplegado.

Referencias oficiales: [cliente JavaScript](https://guacamole.apache.org/doc/gug/guacamole-common-js.html), [Guacamole.Client](https://guacamole.apache.org/doc/guacamole-common-js/Guacamole.Client.html), [WebSocketTunnel](https://guacamole.apache.org/doc/guacamole-common-js/Guacamole.WebSocketTunnel.html).
