# Catálogo descargable · entrega del 13 de octubre de 2026

Se adaptaron 35 retos existentes a ejercicios locales con datos sintéticos. DFIR-01 mantiene su expediente correlacionado; LAB-01 y ESC-01-RECON conservan sus VMs y flags dinámicas. Los 38 retos están publicados y asignados al grupo 45HY (verde) en la instalación local.

## Para estudiantes

1. Iniciar sesión con una cuenta del grupo verde y seleccionar un reto.
2. Iniciar la corrida y pulsar **Descargar ejercicio completo (.zip)**.
3. Extraer el ZIP, leer README.txt y resolver el objetivo con herramientas locales. Los archivos SHA256SUMS.txt permiten verificar la integridad de lo descargado.
4. Introducir la respuesta en **Validar respuesta**. Una respuesta correcta habilita **Registrar puntos**; este último botón completa el reto.
5. Cerrar el ejercicio. La corrida dura cuatro horas y una nueva corrida genera otros datos. La puntuación se otorga una sola vez por reto.

Python 3 es suficiente para analizar JSON, Base64, XOR, RSA didáctico, hashes y bytes. PowerShell permite calcular hashes; Wireshark sirve para el PCAP. No es necesario contactar direcciones de las evidencias: todos los registros son ficticios.

## Alcance pedagógico

Los ejercicios web son revisión de código, registros o copias de archivos. Los escenarios de movimiento lateral y exfiltración son análisis de evidencias sintéticas. FOR-03 es una muestra binaria educativa, no un volcado completo de memoria. PWN-01 es cálculo de desplazamientos y direcciones en una pila simulada, no explotación de un servicio real. Los nombres y objetivos indican esta adaptación.

Las prácticas adaptadas tienen nivel básico o medio acorde con su contenido. Se conservaron códigos, categorías, puntuaciones e historial existentes. DFIR-01 mantiene el ejercicio avanzado de correlación.

## Operación

La API crea los archivos bajo demanda con una semilla privada distinta por usuario y corrida. El servidor guarda el hash de una flag dinámica; la entrega solo al validar la respuesta. El ZIP no contiene esa flag ni la respuesta privada del validador. La respuesta analítica sí puede reconstruirse a partir de las evidencias, que es el objetivo.

Los endpoints de descarga y respuesta comprueban propietario, pertenencia a un grupo asignado, publicación y caducidad. Las corridas locales no reservan VMs ni crean conexiones Guacamole.

La conversión conserva las flags antiguas desactivadas y registra nombre, instrucciones, referencias, dificultad y IDs de flags activas anteriores en eventos `challenge.offline.convert`. No modifica el esquema, elimina historial ni recalcula puntuaciones ganadas. Su repetición es idempotente.

Para aplicar a otra copia de **este catálogo existente**, después de desplegar el código:

```powershell
Get-Content backend/configure_offline_catalog.py | docker compose exec -T api python - --group 45HY
Get-Content backend/configure_offline_catalog.py | docker compose exec -T api python - --group 45HY --apply
```

La primera orden ensaya la conversión y revierte la transacción. La segunda confirma los cambios. Se exige un grupo activo y los 35 códigos del catálogo; se rechazan conversiones con corridas activas. No se publican automáticamente otros borradores que se creen en el futuro. En la entrega local se reconciliaron también los grupos 1, 3, 4 y 5 con Guacamole para reflejar las referencias actualizadas. Los despliegues posteriores deben usar la sincronización habitual de grupos si modifican dichas referencias.

## Validación realizada

- Compilación de TypeScript y Vite correcta.
- 181 pruebas de backend correctas; los tests de contenido comprueban los 35 ejercicios con 20 semillas cada uno (700 casos), mediante solutores que usan solo archivos públicos.
- Prueba de integración PostgreSQL de los 35: inicio, reutilización, ZIP, solución independiente, rechazo de respuesta incorrecta, aislamiento de usuario, puntos sin duplicados, cierre, rechazo de flags antiguas y caducidad. Rollback confirmado, sin usuarios de prueba ni puntos persistidos.
- Integración de DFIR-01: solución, 500 puntos una sola vez, cierre y rechazo de flag anterior; rollback confirmado.
- Comprobación final: 38 publicados, asignados al grupo verde y con una flag activa cada uno.
- API saludable; puertos SSH de Kali/víctima y puerto 18081 de evidencia accesibles. Autenticación SSH del inyector comprobada sin escribir archivos. Esto no sustituye una sesión completa de alumno en los dos laboratorios reales.

## Límite de la entrega

Esta es la publicación de la instalación local en http://localhost:8081/. Los ejercicios descargables requieren que la plataforma esté encendida para iniciar, descargar y registrar puntos; el análisis de archivos se hace sin servidor de retos. LAB-01 y ESC-01 siguen requiriendo sus VMs encendidas. El despliegue institucional permanece pendiente de recibir el servidor.
