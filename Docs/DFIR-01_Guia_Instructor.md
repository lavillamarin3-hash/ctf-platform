# DFIR-01 · Correlación forense de incidente

Reto avanzado de 500 puntos. El expediente es sintético y se genera por estudiante y corrida. Se ejecuta en la plataforma, sin reservar las VM de LAB-01 o ESC-01. Cada corrida dura dos horas.

## Activación

1. Entrar como administrador o instructor y abrir **Retos**.
2. Localizar **DFIR-01**. Si no existe, pulsar **Crear o localizar borrador DFIR-01**.
3. Editar el reto y conservar el activo **DFIR-CASE**, con una única flag dinámica activa.
4. Seleccionar el grupo de prueba y publicar cuando corresponda.
5. Entrar con un estudiante de ese grupo, iniciar el reto y revisar el expediente.

Crear el borrador no lo publica ni lo asigna. La plantilla de flag del catálogo es descriptiva: DFIR-01 deriva su flag en el backend a partir de la corrida y del secreto HMAC del servidor. Cambiar esa plantilla no cambia el formato efectivo de DFIR-01. No rotar el secreto HMAC durante una corrida.

## Recorrido del estudiante

Descargar las fuentes de autenticación, HTTP y red y comprobar los SHA-256 de sus contenidos UTF-8. Las balizas permiten calcular los desfases constantes de autenticación y HTTP frente al reloj de red. Correlacionar `session` y `request` y aplicar todas las condiciones descritas en el expediente. Introducir sesión, usuario, solicitud, destino y hora UTC de autenticación (ISO 8601 con zona horaria).

Una correlación correcta entrega la flag. **Enviar flag y registrar puntos** usa la validación habitual del backend; no hay que volver a escribirla. Copiar flag permite conservarla en el portapapeles si se necesita. Cerrar el caso impide nuevas consultas o respuestas de esa corrida. Los archivos descargados por el alumno permanecen en su equipo; el cierre no los elimina.

La reapertura genera otro expediente y otra flag. Los puntos se otorgan una sola vez por estudiante y reto.

## Verificación realizada

- Pruebas unitarias y de ciclo del backend: 179 pruebas aprobadas en la implementación inicial.
- Prueba posterior contra PostgreSQL real, dentro de una transacción revertida: inicio, reutilización de corrida, resolución independiente usando solo evidencias públicas, respuesta incorrecta, aislamiento entre usuarios, 500 puntos una sola vez, cierre, reapertura y rechazo de la flag anterior.
- Confirmado tras la prueba: el usuario de QA no quedó guardado y se conservó el estado de publicación original.
- Pendiente de aceptación: recorrido visual completo con estudiante de un grupo elegido por el instructor.

## Límites del ejercicio

El caso entrena correlación y normalización temporal sobre registros simulados. No incluye tráfico real, adquisición de memoria ni una explotación de servicios. La dificultad indicada es la del catálogo y debe calibrarse con el grupo piloto.

## Estado del piloto

DFIR-01 está publicado y asignado exclusivamente al grupo 45HY (verde). El recorrido visual del estudiante queda disponible para la aceptación del instructor.
