# Operación Cóndor: guía del estudiante

Reto **WEB-CONDOR — Operación Cóndor: acceso al centro de mando**.
El portal, sus cuentas y sus datos pertenecen al laboratorio educativo.

El objetivo es investigar una aplicación web desde Linux, justificar qué cuenta permite publicar, comprobar su contraseña con el diccionario del ejercicio y demostrar el acceso publicando un comunicado con un título elegido por ti. La flag valida el resultado técnico; las evidencias y tu explicación permiten al tutor evaluar la comprensión del procedimiento.

## Acceso y alcance

1. Entra en Cociber CTF con tu cuenta de estudiante y abre el reto asignado a tu grupo.
2. Pulsa **Iniciar ejercicio** y consulta la **IP víctima** y los **puertos autorizados** de tu corrida.
3. Abre la **terminal SSH de Kali** integrada. Ejecuta allí los comandos de investigación y crea una carpeta propia para las evidencias de esta corrida.
4. Trabaja únicamente contra la IP y los puertos que muestra el reto. `localhost` dentro de Kali identifica a Kali, no al equipo donde abriste Cociber CTF.

SSH proporciona acceso a tu puesto Kali. La comprobación de contraseñas corresponde al formulario **HTTP de Cóndor**, no al servicio SSH ni a las cuentas de Linux.

## Misión

1. Identifica el servicio web y registra qué evidencia permitió localizarlo.
2. Investiga los recursos públicos del portal. Descarga y analiza los artefactos del ejercicio para determinar el usuario que cumple la regla de publicación.
3. Justifica la elección de la cuenta usando los registros y su estado vigente. Una coincidencia en el nombre no basta.
4. Utiliza únicamente el diccionario acotado del laboratorio para comprobar el acceso de esa cuenta. Compara la respuesta de un acceso fallido con una autenticación válida.
5. Desde Kali, inicia una sesión HTTP y publica un comunicado. El **título es libre, de 3 a 100 caracteres**, y el **cuerpo debe tener de 10 a 1000 caracteres**. Puedes describir brevemente el hallazgo realizado.
6. Recoge la flag que aparece después de publicar y envíala en el panel de validación de Cociber CTF. Comprueba el resultado y los puntos registrados.
7. Cierra la sesión del portal cuando termines y pulsa **Cerrar ejercicio** en Cociber CTF.

## Evidencias para el tutor

- Comandos y resultados relevantes del reconocimiento, con la IP y el puerto dentro del alcance asignado.
- Archivos analizados y explicación de la correlación que identifica la cuenta válida y descarta las demás.
- Evidencia de la diferencia entre autenticación fallida y válida, ocultando contraseñas, cookies y otros datos de sesión.
- Título elegido, evidencia del comunicado publicado y resultado de validación en Cociber CTF. Oculta la flag en el informe que compartas.
- Explicación breve de los problemas encontrados y de las medidas que impedirían repetirlos en una aplicación real.

Guarda tus evidencias en la carpeta de tu corrida. No publiques la contraseña, las cookies ni la flag en el comunicado o en documentos compartidos.

## Tiempo y ayudas

La configuración base es de **45 minutos y 250 puntos**, con **tres pistas progresivas**. Cada pista utilizada descuenta **10 % del puntaje base**. Al vencer el plazo se habilitan la explicación y la finalización asistida con **25 % del puntaje base**. Si el tutor ajustó estos valores, se aplican los que muestra Cociber CTF.

El contador empieza en el primer inicio y no se reinicia al reabrir. Los puntos ya obtenidos se conservan. Utiliza el panel de ayudas cuando necesites orientación.

## Condiciones del laboratorio

Kali y el portal son compartidos. Cerrar la corrida cierra su terminal, pero no apaga la web, no borra los comunicados ni cierra automáticamente la sesión HTTP del portal. Cada sesión debe publicar su propio comunicado para mostrar la flag; la flag pertenece a la instancia compartida.

Si no aparece la terminal o el servicio web no responde, comunica al tutor el error, la IP, el puerto y la hora de la prueba, sin enviar credenciales. El tutor debe comprobar el acceso SSH, los permisos del grupo y la disponibilidad de la víctima.
