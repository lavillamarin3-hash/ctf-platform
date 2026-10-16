# Ayudas, tiempo y puntuación

El administrador o instructor configura un tiempo común por reto, de 1 a 1440 minutos, entre una y tres pistas consecutivas, y el porcentaje de puntos que queda al vencer. Cada pista tiene título, texto y descuento propio entre 0% y 100%; la suma de descuentos no puede superar 100%. Abrir una pista repetida no vuelve a descontar. Al vencer se aplica exactamente el porcentaje configurado sobre los puntos base, sin restar además las pistas. El servidor calcula con enteros y redondea hacia abajo.

Si no hay configuración propia, se mantienen tres pistas de 10% y 25% al vencer. La duración predeterminada es de una hora para VMs, SSH y HTTP, cuatro horas para ejercicios descargables y dos horas para el expediente DFIR local anterior. No hay excepciones de tiempo por estudiante.

El primer inicio guarda una copia privada de la política, los puntos base y el plazo para cada estudiante y reto. Las ediciones posteriores afectan a quienes aún no empezaron; no cambian textos, costes, duración ni solución personalizada de una copia ya creada. Cerrar y reabrir conserva las pistas y el primer plazo. Si aún queda tiempo, los recursos de la nueva corrida caducan en ese mismo plazo; si ya venció, se permite una nueva ventana para practicar, con el porcentaje reducido del aprendizaje original. Las reservas Redis, sesiones y registros de práctica usan la caducidad real de la corrida.

Los ledgers anteriores sin copia de política conservan sus tres pistas de 10%, su porcentaje de 25% y su plazo original. Las corridas anteriores a la función de ayudas no reciben plazos retroactivos: si la pantalla indica que las ayudas aún no están activadas, hay que cerrar e iniciar una nueva corrida. Los puntos ya registrados en `challenge_completions` no se recalculan.

Cuando vence el plazo, la pantalla solicita al servidor la explicación y la respuesta. Antes de ese momento el servidor rechaza la solicitud y los datos ocultos no viajan en el catálogo ni en los metadatos del alumno. Después de revisar la solución, el estudiante puede pulsar **Registrar aprendizaje**: se concede una única finalización asistida con el porcentaje configurado, aunque sea 0%. Esta acción no crea un envío ficticio de flag correcta ni reactiva recursos o terminales expirados. El ranking conserva su criterio habitual y suma los puntos realmente otorgados.

La solución personalizada opcional sustituye los pasos de la explicación. Cuando el ejercicio genera una respuesta verificable, también se muestra la correspondiente a la corrida. En las pistas y la explicación se puede usar `{{RUN_ID}}`: se sustituye por el identificador de la corrida al mostrar el texto. La edición administrativa devuelve estos marcadores y no incorpora identificadores de prueba.

Los casos de lógica, DFIR, SSH y HTTP regeneran el material de su propia corrida. Las nuevas corridas dinámicas de LAB-01 y ESC-01 también muestran su flag original al vencer el plazo: se deriva la parte `RAND` mediante HMAC con el secreto existente y el contexto único de corrida, usuario, reto, flag y plantilla. Se conserva el formato de las plantillas y la validación habitual contra el hash.

La versión de derivación y el contexto original (plantilla y nombre de usuario incluidos) quedan en un evento de auditoría de la corrida, en la misma transacción que su hash. No se almacena la clave HMAC ni la flag en claro. Antes de mostrar una respuesta reconstruida, el servidor verifica que coincide con el hash persistido. Por eso editar la plantilla o el nombre de usuario después no cambia la respuesta original. Hay que conservar `FIELD_HMAC_SECRET` y esos eventos de auditoría para poder reconstruirla; si no se puede verificar, no se inventa una respuesta.

La derivación de respuestas no modifica el generador global ni otras prácticas, no requiere migración propia y solo se aplica a corridas nuevas de esos dos retos. Las corridas anteriores sin marcador siguen usando sus hashes originales y muestran el procedimiento de resolución; no se intentan regenerar sus flags aleatorias. Las flags estáticas elegidas explícitamente por el instructor tampoco se cambian.

## Migración y activación

Desde `backend`, usando la configuración normal de la API:

```bash
python migrate_learning.py --check
python migrate_learning.py --apply
python migrate_learning_policy.py --check
python migrate_learning_policy.py --apply
```

En ambos scripts, el modo de consulta es el predeterminado. `migrate_learning.py --apply` crea idempotentemente las tablas `challenge_learning_progress` y `challenge_hint_reveals` si faltan. `migrate_learning_policy.py --apply` añade las columnas JSON anulables `challenges.learning_policy` y `challenge_learning_progress.policy_snapshot`, y amplía la restricción de descuento a 0..100. Esta segunda migración explícita requiere PostgreSQL y las tablas anteriores. No rellena snapshots históricos ni cambia revelaciones, finalizaciones o puntos. Hay que aplicar ambas antes de desplegar el backend configurable. No se necesita cambiar permisos Guacamole.

Los servicios de práctica HTTP/SSH permanecen activos mientras exista una configuración de corrida no caducada, aunque pase una hora sin actividad. Al actualizar su script se reemplaza la fuente atómicamente y solo se recarga el proceso de práctica del mismo usuario con ruta y argumentos exactos. Los registros de otras corridas y la clave de host SSH se conservan; no se reinicia el SSH del sistema ni se modifican cuentas.

## Contrato del cliente

- Crear/editar reto admite `learning_policy: {duration_minutes, expired_points_percent, hints: [{title, content, penalty_percent}], solution_text?}`. Título: 1..120 caracteres; texto de pista: 1..4000; solución: hasta 12000. Solo administración e instructor reciben la política privada y la política efectiva de los retos antiguos. Omitir `learning_policy` en un PUT conserva la configuración existente; un `null` explícito restablece los valores predeterminados para futuros comienzos.
- `GET /api/v1/runs/{id}/learning`: puntos base/disponibles, primer plazo, vencimiento, `expired_points_percent`, `hint_count`, títulos/descuentos por pista y contenido solo de las ya abiertas, estado de solución y finalización.
- `POST /api/v1/runs/{id}/learning/hints/{1..3}`: abre una pista configurada, exige las anteriores y una corrida activa antes del plazo; devuelve los mismos metadatos.
- `POST /api/v1/runs/{id}/learning/solution`: después del plazo devuelve además `{steps: string[], answer: string|null, note?: string}`.
- `POST /api/v1/runs/{id}/learning/complete`: después del plazo y de revelar la solución, registra el aprendizaje asistido y devuelve el contrato habitual de finalización. Un segundo intento otorga cero puntos adicionales.

Todas las operaciones verifican propietario, publicación y asignación actual. Las respuestas no se almacenan en caché. Un lock del usuario y otro del ledger serializan revelaciones y finalización; restricciones únicas impiden duplicar el ledger, una pista o la finalización del reto. La concesión normal de puntos usa la misma política, aunque el usuario cierre y empiece otra corrida.

## Verificación

La configuración administrativa quedó desplegada y verificada el 16 de octubre de 2026. La aceptación actual, las pruebas sobre PostgreSQL y las VMs, y la comparación de los doce puntajes históricos se registran en [Configurar tiempo y pistas](CONFIGURAR_TIEMPO_Y_PISTAS.md#verificación-del-16-de-octubre-de-2026).

Aceptación anterior del 15 de octubre de 2026: 228 pruebas de backend y 25 de frontend aprobadas; compilación TypeScript/Vite correcta. La interfaz mostró el plazo original, las pistas ordenadas y los puntos disponibles. Las nuevas corridas de LAB-01 y ESC-01 verificaron su respuesta reconstruida contra la flag inyectada y su hash, incluidas la protección antes del plazo, la edición posterior de usuario/plantilla y la compatibilidad con corridas antiguas. Se conservaron los once resultados previos y sus puntajes. Estos resultados corresponden a la versión previa a la configuración administrativa; la validación nueva se registra con su despliegue.

`tests.test_learning` usa SQLite real para tablas, restricciones, preservación histórica y endpoints. Simula los locks que SQLite no implementa y comprueba que las consultas de producción compilan con `FOR UPDATE` para PostgreSQL. Incluye peticiones concurrentes de pista/envío y de finalización asistida, límites de tiempo, permisos, pistas repetidas/ordenadas, reapertura y una finalización de cero puntos. Las pruebas nuevas cubren costes variables, límites de configuración, snapshots inmutables, políticas antiguas, privacidad administrativa y porcentajes 0/100. `tests.test_learning_policy_migration` comprueba el plan aditivo e idempotente. `tests.test_run_lifecycle` valida la caducidad real de VMs/SSH/HTTP y la reserva Redis, además del inicio, cierre, inyección y puntuación. Las pruebas de servicios comprueban la continuidad de corridas largas, su revocación y la actualización segura del daemon SSH. Ninguna de esas pruebas contacta las VMs ni una base de datos externa.
