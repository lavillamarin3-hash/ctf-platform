# Configurar tiempo, pistas y descuentos

1. Entrar como administrador o instructor y abrir **Retos**.
2. Crear un reto o pulsar **Editar** en uno existente.
3. En **Tiempo, pistas y puntaje**, indicar la duración común en minutos.
4. Escribir entre una y tres pistas, cada una con título, texto y descuento porcentual.
5. Elegir qué porcentaje del puntaje base queda al agotarse el tiempo. Se puede añadir una explicación propia en **Solución del instructor**.
6. Pulsar **Crear reto** o **Guardar cambios**.

El contador empieza cuando cada estudiante inicia su primera práctica. Cerrar y reabrir conserva el plazo y las pistas usadas. La política de una práctica iniciada se conserva aunque luego se edite el reto; los cambios se aplican a quienes todavía no lo hayan iniciado. Los puntos ya obtenidos se mantienen.

Ejemplo con 250 puntos: una pista del 10% deja 225; otra del 20% deja 175. Si al vencer se configuró el 25%, quedan 62 puntos, redondeando hacia abajo. El porcentaje del vencimiento sustituye los descuentos de pistas.

Las pistas cerradas y la solución del instructor se mantienen privadas. El alumno ve el coste antes de abrir cada pista. La solución se habilita al finalizar el plazo.

## Actualizar una instalación existente

Desde la carpeta del proyecto, después de obtener el código nuevo:

```bash
docker compose build api web
docker compose run --rm --no-deps -v "${PWD}/backend:/app:ro" api python migrate_learning.py --apply
docker compose run --rm --no-deps -v "${PWD}/backend:/app:ro" api python migrate_learning_policy.py --apply
docker compose up -d --no-deps api web
```

Estas migraciones son idempotentes y no recalculan puntajes. La segunda añade dos columnas JSON privadas y amplía el rango admitido para descuentos, conservando el historial.

Consultar [Ayudas, tiempo y puntuación](AYUDAS_Y_PUNTAJE.md) para el contrato técnico y la compatibilidad con corridas anteriores.

## Verificación del 16 de octubre de 2026

Se aprobó la suite completa de 247 pruebas de backend y, después de corregir las instrucciones heredadas, 38 pruebas dirigidas que incluyen tres casos nuevos. También pasaron 31 pruebas de frontend, cuatro archivos de regresiones con 22 comprobaciones y la compilación de TypeScript/Vite.

La migración real de PostgreSQL ejecutó cuatro instrucciones y una consulta posterior confirmó que no quedaban cambios pendientes. La integración con rollback comprobó una política de siete minutos, dos pistas con costes del 10% y 30%, privacidad, reapertura sin reiniciar el plazo, solución al vencer y crédito único del 40%. No quedaron usuarios ni resultados QA.

La sesión administrativa guardó y volvió a abrir la configuración de CTF-LNX-03 con sus valores vigentes: 240 minutos, tres pistas del 10% y 25% al vencer. Las doce finalizaciones anteriores conservaron exactamente sus puntajes. Las prácticas SSH y HTTP se comprobaron desde Kali hacia LNX-VICT, incluyendo validación, puntuación única, cierre y revocación.
