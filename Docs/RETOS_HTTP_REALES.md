# Prácticas HTTP entre Kali y LNX-VICT

ESC-06-WEBAUTH y ESC-07-EXPOSED están preparados para las máquinas existentes: Kali `192.168.146.134` y LNX-VICT `192.168.146.137`. Cada corrida prepara una evidencia dinámica válida durante una hora. Ambos ejercicios abren la terminal Kali integrada y usan el servicio de práctica HTTP en el puerto 18082 de la víctima.

ESC-06 prueba doce candidatos contra una cuenta HTTP Basic temporal con Hydra, recupera la flag con curl y registra 250 puntos una sola vez. Su clasificación es [T1110.001 — Password Guessing](https://attack.mitre.org/techniques/T1110/001/), que incluye servicios HTTP.

ESC-07 consulta robots.txt, descubre un directorio de respaldo expuesto y recupera su archivo de evidencia, por 150 puntos. Se clasifica didácticamente como reconocimiento activo ([T1595 — Active Scanning](https://attack.mitre.org/techniques/T1595/)). robots.txt proporciona una pista; no es un control de acceso.

El servidor Python usa únicamente la biblioteca estándar y se ejecuta como el usuario del inyector, sin sudo. Escucha en la IP de la víctima y admite solo conexiones desde Kali. Los registros temporales viven en `~/.ctf-http-practice/ctf<ID>.json`, con permisos privados; el servicio publica únicamente rutas explícitas de práctica y no accede al sistema de archivos de la VM a partir de entradas HTTP. La contraseña se almacena por hash. La flag y la contraseña elegida no aparecen en la API de instrucciones.

El cierre elimina el registro de la corrida. El servicio comprueba su existencia y caducidad en cada petición, y cierra la conexión HTTP tras responder. Cerrar o caducar también bloquea el acceso a las instrucciones/terminal del ejercicio en la plataforma. Reiniciar la VM requiere cerrar la corrida antigua e iniciar una nueva para arrancar de nuevo el servicio. El proceso termina tras una hora sin peticiones.

Publicación explícita al grupo verde, preservando el catálogo, puntuaciones e historial existentes:

```powershell
Get-Content backend/configure_http_catalog.py | docker compose exec -T api python - --group 45HY
Get-Content backend/configure_http_catalog.py | docker compose exec -T api python - --apply --group 45HY
```

La primera orden ensaya con rollback; la segunda publica y asigna. Ejecutarlas otra vez no crea retos, flags ni asignaciones duplicados. Una colisión de códigos con otro escenario aborta la operación.

Validación: 190 pruebas de backend aprobadas y compilación TypeScript/Vite correcta. La integración sobre las VMs reales comprobó Hydra HTTP Basic desde Kali, credenciales incorrectas rechazadas, recuperación de flags, puntos únicos, revocación y los pasos robots -> backup -> archivo. Comprobó también propiedad de la corrida, permisos de terminal, reutilización, catálogo idempotente y rollback sin catálogo/usuarios/puntos QA persistidos. La prueba SSH existente volvió a comprobarse con Hydra real, incluyendo la contraseña al final de los doce candidatos.

Los dos nuevos ejercicios quedan publicados para verde. El catálogo pasa de 38 a 40: cinco ejercicios con víctima real y 35 casos de análisis en Kali.

Aceptación visual con el alumno: ambos escenarios mostraron sus comandos y la terminal Kali conectada. La sesión de ESC-06 se cerró sin enviar flag. ESC-07 realizó desde la terminal integrada una petición HTTP a `/practice/416/robots.txt` y recibió la ruta del respaldo. Se dejó abierto para practicar y se guardó una captura del resultado. No se otorgaron puntos durante esta aceptación.
