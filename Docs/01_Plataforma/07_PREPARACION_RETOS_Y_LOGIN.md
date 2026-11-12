# 07. Recorrido de preparación de retos y login a pantalla completa

Entrega del **12 de noviembre de 2026**. Se actualizan API y web; no cambia el esquema de BD ni se publican retos automáticamente.

## 1. Actualizar la instalación existente

Sigue los pasos 1 a 4 de [05. Actualizar la plataforma](05_MODALES_Y_GESTION_USUARIOS.md): transferir primero la revisión al checkout real, conservar `.env.fresh`, cerrar corridas y esperar su limpieza, construir API/web, comprobar la instalación, recrear servicios y reiniciar el worker previamente activo.

La ruta observada es `/home/lab-ctfweb/ctf-platform`; conserva el WorkingDirectory corregido. No ejecutes inicialización de base de datos, bootstrap ni seed para esta actualización. Deben llegar también `frontend/src/fresh/preparation.ts` y `frontend/src/fresh/PreparationRoadmap.tsx`.

## 2. Preparar un reto desde la interfaz

1. Entra como administrador o instructor y abre **Preparación de retos**. También puedes pulsar **Nuevo reto** desde Retos.
2. Selecciona un reto existente en el selector superior o elige **Nuevo reto**. La selección se mantiene al navegar entre módulos durante esta sesión de la página.
3. Sigue los pasos: **Máquinas → Laboratorios → Crear reto → Integración → Jugadores → Piloto → Publicar**.
4. Los botones llevan al módulo correspondiente o abren el formulario. Vuelve mediante **Gestionar preparación**, visible sobre el contenido de cada módulo.
5. Al guardar el borrador, aparece «Reto creado correctamente» y el paso de creación queda completado. Esto no lo publica.
6. Asigna al menos un grupo con jugadores activos. Si el grupo está vacío, crea el grupo con sus jugadores y asígnalo; crear una cuenta sin pertenencia a grupo no completa el paso.
7. Ejecuta el piloto. Mientras está en cola, preparando o limpiando, consulta **Corridas**. La aprobación solo se completa cuando la plataforma registra éxito y limpieza.
8. Pulsa **Publicar reto** cuando todos los requisitos estén completos. La tabla inferior permite continuar la preparación de cualquiera de los otros retos.

## 3. Qué acredita cada estado

El avance se calcula desde la API: víctima real del reto, Kali disponible, pertenencia de ambas a laboratorios disponibles, integración habilitada, grupos con jugadores activos, piloto aprobado y estado publicado. No se guardan marcas manuales en el navegador.

Si se drena una máquina o desaparecen los jugadores de un grupo, el recorrido vuelve a mostrar el requisito pendiente aunque el reto hubiera sido publicado antes. La publicación histórica se conserva: el panel no modifica la BD para ocultar ese cambio. Una máquina ocupada puede causar cola; no equivale a un fallo de preparación.

El refresco es periódico. Si falla la consulta, se indica que el estado no está actualizado y se bloquean las acciones de preparación hasta recuperarlo. Un estado «Disponible» sigue siendo la confirmación guardada por el operador: no se realiza una prueba de red nueva en cada refresco.

El paso Integración no habilita servicios por sí mismo. ESC-01, Windows A→B y el diseño FTP siguen pendientes según sus guías. Un piloto SSH tampoco comprueba un escritorio RDP; sigue [06. RDP](06_DIAGNOSTICO_RDP_GUACAMOLE.md) cuando el reto necesita interfaz gráfica.

## 4. Login

La pantalla de acceso ocupa el ancho y alto disponibles con dos paneles, sin tarjeta exterior. En pantallas pequeñas los paneles se apilan y el contenido puede desplazarse sin quedar recortado. El pie institucional se muestra únicamente en el login:

> Universidad de las Fuerzas Armadas «ESPE» · COCIBER
> Todos los derechos reservados.

Se conservan tema claro/oscuro, mostrar contraseña, mensajes de error y cambio obligatorio de contraseña inicial. El pie institucional no se añade a los módulos internos.

## 5. Aceptación en el servidor

- Recargar con Ctrl+F5 y revisar login en escritorio y móvil, con el footer inferior visible al llegar al final.
- Crear un borrador de prueba y confirmar que su paso de creación cambia a Completado, manteniendo pendientes los demás.
- Revisar un reto con integración deshabilitada: no debe poder ejecutar piloto ni publicarse.
- Asignar un grupo vacío y luego uno con jugadores activos: solo el segundo completa Jugadores.
- Completar un piloto y su limpieza, publicar y comprobar que el jugador del grupo ve el reto.
- Cambiar de módulo y confirmar que el recorrido sigue mostrando el reto elegido; cerrar sesión y verificar que el jugador no ve administración ni el recorrido.

Las verificaciones locales de interfaz y lógica no sustituyen la prueba del worker y de las VM reales. Esta entrega no cambia nftables ni instala RDP en Nutanix automáticamente.

## Validación local de esta entrega

Compilación fresh correcta; 9 pruebas nuevas del recorrido y 3 de sesión aprobadas; 27 pruebas unitarias fresh aprobadas; una prueba de integración en PostgreSQL local verificó el conteo de jugadores activos. En navegador se comprobó login de escritorio/móvil, footer, recorrido, apertura/cierre del modal y navegación entre módulos con datos simulados. Los 22 bloques de comandos nuevos pasaron la revisión de sintaxis; no se ejecutaron en Nutanix.
