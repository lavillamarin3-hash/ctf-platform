# Terminal SSH embebida · Requisitos antes de implementar

## Objetivo UX

Desde la vista del estudiante, el reto debe poder abrir su entorno SSH dentro de la misma página, sin abandonar la navegación principal de la plataforma.

La experiencia prevista es:

```text
Detalle del reto
   |
   +-- Panel del laboratorio
   |      +-- Estado
   |      +-- VM/IP
   |      +-- Abrir terminal
   |
   +-- Terminal embebida
          +-- Conectando
          +-- Sesión activa
          +-- Desconectar
```

## Requisito técnico principal

Apache Guacamole no se integra correctamente como una simple terminal SSH local del navegador. La integración web debe hablar con el cliente/túnel de Guacamole.

La opción de integración profunda es utilizar `guacamole-common-js` y crear un `Guacamole.Client` asociado a un túnel; la API de Guacamole expone `connect(data)` para establecer la sesión. El proyecto debe proporcionar el túnel y la información de conexión de forma segura.

## Opciones de integración

### A. Iframe

Ventajas:
- Es la prueba más rápida.
- Permite reutilizar la interfaz web existente de Guacamole.

Limitaciones:
- La UX depende del login/sesión de Guacamole.
- El control visual y de eventos dentro de la plataforma es limitado.
- Deben revisarse CSP, políticas de frame y same-origin/reverse proxy.

### B. `guacamole-common-js`

Ventajas:
- La terminal vive dentro del layout de la aplicación.
- Podemos controlar estados de conexión, resize, reconexión y cierre.
- La vista puede mostrar simultáneamente instrucciones, terminal y envío de flag.

Requisitos adicionales:
- Empaquetar la librería en el frontend.
- Crear/obtener el túnel apropiado desde backend/Guacamole.
- Diseñar el manejo de credenciales/sesión sin exponer secretos de servicio.
- Escuchar eventos de teclado, pantalla, disconnect y resize.

## Autenticación

La cuenta de servicio de Guacamole **no debe llegar al navegador**.

La plataforma necesita un mecanismo para que el navegador del estudiante disponga de una sesión/token de Guacamole de corta duración o una sesión SSO compatible. La URL opaca que hoy construye el backend para `#/client/...` no reemplaza por sí sola la autenticación del usuario final.

## Requisitos de infraestructura

- Guacamole real accesible desde el navegador del estudiante.
- Backend accesible desde el frontend.
- Guacamole y la plataforma deben ser compatibles con HTTPS cuando la plataforma funcione por HTTPS.
- WebSocket/túnel de Guacamole permitido entre navegador y servidor, según el modo de integración.
- DNS/hostname coherente o reverse proxy estable.
- La conexión SSH de la víctima debe existir en Guacamole.
- El usuario del estudiante debe tener permiso `READ` sobre la conexión, o la plataforma debe emitir una autorización temporal equivalente.

## Requisitos de seguridad

- Nunca enviar `GUACAMOLE_SERVICE_PASSWORD` al frontend.
- Nunca enviar la clave privada `FLAG_INJECTOR_SSH_PRIVATE_KEY` al frontend.
- Separar cuenta del inyector y cuenta utilizada por el estudiante.
- Mantener validación de host SSH cuando sea posible.
- El backend debe vincular la sesión remota a un `ChallengeRun`.
- Cerrar/revocar la sesión al terminar el `ChallengeRun`.

## Cambios de frontend previstos

No hace falta modificar el modelo de datos para esta funcionalidad.

Se añadirá un componente específico, por ejemplo:

```text
frontend/src/components/player/EmbeddedGuacamoleTerminal.tsx
```

y el controlador conservará la responsabilidad de iniciar/cerrar el `ChallengeRun`.

La vista `PlayerLaboratory` mostrará el componente en lugar de limitarse a `window.open(...)`.

## Criterios de aceptación UX

- La terminal ocupa la mayor parte del panel sin ocultar el contexto del reto.
- El usuario conoce siempre a qué VM/IP está conectado.
- Existe estado visible: `Conectando`, `Conectado`, `Desconectado`, `Error`.
- El botón de cerrar sesión ejecuta el cierre del `ChallengeRun` y la limpieza de la VM.
- El cambio a modo claro mantiene contraste y legibilidad dentro del panel de terminal.
- En pantallas pequeñas la terminal pasa a una vista de altura reducida y controles apilados.
