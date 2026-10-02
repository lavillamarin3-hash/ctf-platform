# Guía del administrador: reto con flag estática en una VM

Esta guía explica **qué hace la plataforma y qué debe preparar el administrador en la máquina del laboratorio**. No contiene flags reales ni credenciales. Aplícala solo a VMs y grupos autorizados. Si el reto ya aparece en **Retos**, edítalo: no crees otra fila con el mismo código.

## Distinción esencial

| Modo | Qué guarda la plataforma | Quién coloca la evidencia en la VM | Qué ocurre al cerrar |
| --- | --- | --- | --- |
| Estática | Hash del valor que el administrador escribió; el valor no se puede recuperar desde el editor | El administrador, **manualmente** y con el mismo valor exacto | Se cierra la sesión, pero el archivo estático **permanece** en la VM |
| Dinámica | Plantilla y hash/huella por corrida; el valor claro se genera en backend | El inyector SSH durante el inicio, si está configurado | Se retira la evidencia de esa corrida y se libera la reserva |

La flag estática **no se instala automáticamente en el PC al pulsar Guardar**. Escribirla en Administración solo permite que el backend valide el envío posterior. Se necesita una segunda acción, fuera de la aplicación, para dejar la misma cadena en un archivo, servicio o evidencia de la VM. LAB-01 es el ejercicio dinámico existente: para aprender el flujo estático usa primero otro código y una ruta de archivo exclusiva; no sobrescribas `/opt/ctf/flag.txt` de LAB-01.

## Antes de crear o editar

1. Confirma que la versión actualizada está desplegada; si `localhost:8081` continúa con los archivos JS/CSS anteriores, lo que edites puede corresponder a otra versión de la aplicación.
2. Comprueba que el reto no tenga corridas activas. El backend bloquea cambios de VM/flag cuando las hay, para no invalidar la evidencia de un estudiante.
3. Comprueba que dispones de una VM encendida y accesible por la red local, una conexión personal de Guacamole/SSH para el estudiante y una cuenta administrativa **separada** para preparar el archivo. Nutanix/Prism no es requisito para servir la web; sin una VM accesible no es posible verificar el recorrido físico.
4. Decide una ruta **propia de ese reto**, por ejemplo `/opt/ctf/retos/RETO-CODIGO/flag.txt` en Linux. No utilices la misma ruta que una flag dinámica ni una VM compartida por otro reto activo.
5. Define el valor en un lugar privado de operación. No lo incluyas en Git, documentos públicos, línea de comandos, historial de shell, capturas ni registros de soporte.

## Configuración en Administración

1. Ve a **Retos**. Pulsa **Editar** si el código ya existe; para uno nuevo, **+ Nuevo reto** y asigna un código único, nombre, categoría, dificultad, descripción, instrucciones, técnica MITRE y puntos.
2. Selecciona **el nombre exacto de la VM** del reto y confirma su conexión SSH/Guacamole. Evita indicar solo el código de un laboratorio que contiene varias VMs: la resolución podría escoger la primera coincidencia. Las instrucciones para el estudiante deben orientar la investigación sin escribir la respuesta. Puedes añadir videos o presentaciones opcionales.
3. En **Validación del reto**, añade una flag con **modo Estática**, una etiqueta y **orden 1**. Escribe el valor exacto una sola vez en el campo protegido. Al editar una flag existente, el campo de valor vacío significa conservar el hash actual; para cambiarla debes proporcionar un valor nuevo.
4. Deja el reto sin publicar hasta terminar la preparación física. Guarda. Si un paso falla, revisa el reto existente y complétalo; no lo dupliques ni alteres la base manualmente.

## Preparación física en Linux

Con acceso administrativo **a la VM del reto**, crea un directorio dedicado y un archivo de evidencia. Los comandos siguientes no contienen la flag:

```bash
sudo install -d -m 0755 /opt/ctf/retos/RETO-CODIGO
sudoedit /opt/ctf/retos/RETO-CODIGO/flag.txt
sudo chmod 0644 /opt/ctf/retos/RETO-CODIGO/flag.txt
sudo test -s /opt/ctf/retos/RETO-CODIGO/flag.txt
```

En `sudoedit`, pega **exactamente el valor configurado en Administración**, guarda y cierra. Sustituye `RETO-CODIGO` por el código real. Ajusta propietario/grupo/permisos a tu escenario: el usuario SSH del estudiante debe poder **leer**, pero no alterar el archivo. En una VM compartida, considera permisos de grupo o una copia aislada por instancia; `0644` es solo una opción sencilla para una VM didáctica aislada. Comprueba la lectura con la identidad estudiantil autorizada sin publicar el contenido en registros.

En una VM Windows, crea un directorio/archivo equivalente mediante el editor de la propia VM y concede lectura, no escritura, a la cuenta del estudiante. Registra la ruta en las instrucciones del reto sin divulgar el valor.

No escribas la flag literal con `echo ...` en una consola: quedaría expuesta en historial, procesos, capturas o auditorías. No la guardes en `.env` ni en un script de despliegue.

## Publicación y prueba de punta a punta

1. En Administración, asigna el reto a un grupo activo con una cuenta de estudiante de prueba. Publícalo cuando el archivo y la conexión estén preparados.
2. Entra **con esa cuenta de estudiante**. Debe ver solo los retos de sus grupos. Abre el reto, pulsa **Iniciar laboratorio** y confirma la VM/conexión esperadas.
3. Desde la terminal integrada, investiga hasta localizar la evidencia. Usa la selección o el portapapeles para pasarla a **Flag lista para enviar**, sin transcribirla. Envía primero una respuesta errónea de prueba y confirma rechazo; luego la correcta y confirma aceptación/puntos.
4. Pulsa **Cerrar laboratorio** y confirma el cierre de acceso/reserva. **El archivo estático continuará en la VM:** el cleanup físico de flags es exclusivo de las dinámicas. Si necesitas restaurar cambios que hizo el alumno, usa tu procedimiento de VM/snapshot o una VM aislada; la plataforma no implementa restauración automática de Nutanix/Prism.
5. Repite con otra corrida. Una flag estática mantiene el **mismo valor**; cada estudiante puede compartirlo. Para evaluación individual y evidencia renovada por corrida, selecciona el modo dinámico con un inyector SSH operativo.

## Si la validación falla

- **«Flag incorrecta»**: comprueba, sin registrar el valor, que archivo y formulario administrativo contienen los mismos bytes (incluyendo mayúsculas, espacios y saltos de línea). El estudiante debe copiar solo la flag, no el prompt de terminal.
- **El reto no aparece**: revisa publicación, grupo activo y pertenencia. La autorización se aplica en backend.
- **No abre SSH**: revisa VM, conexión Guacamole personal, red local y run. Configurar un hash no crea una VM ni una sesión remota.
- **La flag cambia tras reiniciar**: probablemente se mezcló una ruta dinámica con la estática. Usa una ruta exclusiva y evita modificar LAB-01 mientras existan corridas activas.
- **Cambio de valor**: cierra primero las corridas activas; actualiza tanto el archivo de la VM como la flag administrativa. El hash anterior no permite recuperar el valor claro.

La captura de un run que contiene una flag válida debe tratarse como información sensible. Si se compartió, cierra esa corrida y crea otra antes de utilizarla como evaluación; en retos estáticos, sustituye también el valor en la VM y en Administración.
