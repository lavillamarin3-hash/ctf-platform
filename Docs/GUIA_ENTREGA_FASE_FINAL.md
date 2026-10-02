# Entrega de estabilización e integración CTF

## Estado

Código integrado y probado automáticamente. El esquema PostgreSQL, los datos del despliegue y el ZIP original no fueron modificados. No se ejecutaron migraciones ni restauraciones. Se conserva la sección de laboratorio y las capas/patrones existentes.

La aceptación física final todavía requiere construir/desplegar las imágenes con un motor Docker accesible y probar una cuenta de estudiante sobre la VM real. En este editor el pipe Docker está denegado; no se presenta el build de Vite ni los fixtures como prueba de Docker o de SSH físico. Nutanix/Prism no es dependencia para servir la web, pero las VMs de los ejercicios deben estar disponibles por la red local. Sin internet, el build necesita imágenes base y dependencias almacenadas previamente.

## Cambios entregados

- Reto e instrucciones junto a terminal Guacamole real mediante cliente oficial y puente WebSocket autorizado por run; sin iframe opaco ni credenciales técnicas en el navegador.
- Terminal amplia, escala inicial 125% ajustable entre 75% y 200%, foco, teclado, ratón y estados de conexión/reconexión. El tamaño remoto se calcula sobre una caja estable para reducir redibujos al aparecer scrollbars; hay pantalla completa de la conexión y del espacio LAB completo. Solo una conexión remota se monta a la vez.
- SSH/RDP se eligen en el reto únicamente cuando Guacamole registra ese protocolo para la IP de la VM asignada. La elección se vincula al ticket de un uso y se revalida en el WebSocket; el navegador nunca decide un ID de conexión. RDP requiere que el administrador configure en Guacamole la conexión y el permiso READ del estudiante. No se presume que el RDP físico funcione hasta probarlo en la VM real.
- Selección de texto recibida de Guacamole, bloc de notas privado por pestaña/run, botones usar selección/notas, copiar y pegar, campo pegable y feedback de validación backend. No se generan ni validan flags en frontend.
- Sidebar, modo claro suavizado, preferencia global de texto 90-145% persistente, lista de retos con búsqueda por nombre/código/MITRE, categorías/dificultad y responsive móvil/tablet/escritorio.
- Campana de notificaciones con contador y lectura: inicio/cierre, validación y asignaciones detectadas al recargar el catálogo. Conserva como máximo 20 tipos de evento por cuenta en esta pestaña, sin guardar flags, IP ni credenciales y sin afirmar sincronización entre dispositivos.
- Instructor puede añadir hasta 12 videos/presentaciones por reto con título y URL segura. Se guardan en el campo `instructions` existente, sin nuevas tablas. No se inventó material didáctico.
- Reserva rechazada no limpia otra VM ni concede acceso. Reutilización mantiene VM/conexión originales; una nueva corrida dinámica genera otra flag. Cierre/expiración protegen la reserva, desconectan túneles, limpian físicamente solo la evidencia dinámica y liberan la instancia; fallos conservan el estado para reintentar.
- En modo estático, el panel almacena solo el hash y el administrador coloca el mismo valor manualmente en la VM o artefacto. El archivo estático no se borra al cerrar. LAB-01 conserva compatibilidad dinámica para filas heredadas, pero respeta una nueva elección estática explícita sin migrar PostgreSQL. Véase `GUIA_ADMIN_RETOS_FLAGS_ESTATICAS.md`.
- La configuración opcional `FLAG_INJECTOR_FLAG_PATH` admite `{{CODE}}` para separar rutas de flags dinámicas por reto, manteniendo intacto el valor predeterminado `/opt/ctf/flag.txt`. No cambiar esa variable con corridas activas: cerrar y verificar limpieza antes del cambio porque el cierre vuelve a calcular la ruta. Activar el marcador también mueve la ruta física de LAB-01: preparar primero sus materiales y hacer aceptación física antes de reabrir. El inyector escribe archivos, no crea servicios de red ni configura RDP.
- JWT fuera de las URLs del ranking; tickets HttpOnly de un uso para sockets. Tokens Guacamole cifrados y efímeros en Redis, contraseñas fuera de auditorías y parámetros sensibles fuera de respuestas administrativas.
- Edición de recursos no reescribe flags sin cambios. Cambios de activos/configuración de flags se rechazan durante corridas por limpiar; editar no destruye hashes históricos. Un reto ya completado no vuelve a otorgar puntos.
- Dockerfile frontend usa el lockfile con `npm ci`; contextos excluyen dependencias locales, cachés y configuración privada.

## Aplicar a una instalación existente

1. Conservar la copia del código anterior y la configuración privada actual. El paquete no contiene `.env`, contraseñas, volcados de datos ni historial `.git`. No copiar configuraciones de ejemplo sobre las reales.
2. Aplicar únicamente el código actualizado en el checkout/proyecto Docker que ya usa la instalación. Usar el mismo directorio/nombre de proyecto Compose para mantener los volúmenes existentes. Descomprimir en otro directorio y arrancar Compose con otro nombre podría crear volúmenes nuevos; no equivale a actualizar la instalación.
3. Mantener `MANAGE_SCHEMA_ON_STARTUP=false`. Confirmar `PUBLIC_ORIGIN` con el origen real del navegador. La URL de API de Guacamole debe incluir su contexto y ser accesible desde el contenedor API. Redis debe estar disponible y compartido por workers. No cambiar secretos existentes como parte de esta actualización.
4. Desde la raíz del proyecto existente, con Docker habilitado:

```powershell
docker compose config --quiet
docker compose build api web
docker compose up -d --no-deps api web
```

No ejecutar `down -v`, borrar volúmenes, resetear PostgreSQL, activar creación de esquema ni restaurar SQL para aplicar esta entrega. Si hay corridas activas, cerrarlas normalmente desde la plataforma antes de actualizar para verificar su limpieza; no borrarlas en SQL.

5. Iniciar sesión con un estudiante de prueba que tenga LAB-01 asignado. Si su contraseña CTF coincide con Guacamole, la terminal se conecta automáticamente; de lo contrario solicitará la contraseña personal del laboratorio. Nunca ingresar credenciales de servicio o del inyector en esa pantalla.
6. Completar la aceptación física de `VERIFICACION_RELEASE.md`: comando inocuo, obtener/copiar flag, incorrecta/correcta, cierre, ausencia física de flag, liberación Redis, nueva corrida con flag diferente y rechazo de la anterior. Registrar resultados sin valores de flags ni secretos.

## Videos y presentaciones

En administración/instructor, editar el reto y abrir “Videos y presentaciones”. Añadir tipo, título y URL. Videos públicos YouTube se incrustan solo al solicitar reproducir; videos HTTPS MP4/WebM/OGG pueden reproducirse y las presentaciones abren un enlace seguro. No se implementó carga binaria de archivos ni se añadieron videos ajenos a las instrucciones.

Para recursos propios, colocar archivos en `frontend/public/media` antes del build y usar rutas `/media/...`. También se permiten enlaces HTTPS a contenido existente accesible al estudiante. No incluir credenciales en URLs. El contenido debe corresponder al tema del reto y tener permiso de uso.

## Pruebas y reversibilidad

Ver `VERIFICACION_RELEASE.md` para comandos, resultados y límites. Las suites incluyen pruebas unitarias y fixtures de navegador: no son sustituto de la aceptación física.

Se entrega el código fuente completo y un parche revisable contra la base `9f56a6c`. El repositorio de trabajo queda con commit local y estado limpio; el ZIP excluye `.git` para evitar revelar historial/configuración privada. El parche puede revisarse/aplicarse con Git a la misma base, después de guardar cambios locales. Revertir código no requiere borrar/restaurar datos ni cambiar el esquema.

Antes de revertir una instalación, cerrar/limpiar sus corridas usando la versión que las administra. Restaurar el código anterior y reconstruir solo `api`/`web`, conservando configuración y volúmenes. No usar una restauración destructiva de Git o SQL para solucionar diferencias del parche.
