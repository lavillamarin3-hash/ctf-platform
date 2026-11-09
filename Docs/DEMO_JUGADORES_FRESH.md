# Guía del jugador: instalación nueva

Entra con tu cuenta, cambia la clave inicial y abre un reto asignado. Pulsa Iniciar y espera: **en cola** significa que el reto o la Kali todavía están ocupados. La consola aparece dentro del reto cuando la preparación termina. Anota el run_id de 12 caracteres; identifica exclusivamente tu evidencia.

## ESC-02 — Acceso SSH de práctica

**Objetivo:** identificar el servicio didáctico, encontrar una credencial dentro de un diccionario pequeño y recuperar tu evidencia. Herramientas: nmap, Hydra y ssh, desde la Kali asignada.

1. Confirma que el destino es LAB-LNXVICT, `10.10.30.12`, puerto **2222**. El 22 es administrativo y no forma parte del ejercicio.
2. Enumera solo ese puerto y observa el servicio:

   ```bash
   nmap -sV -p 2222 10.10.30.12
   ```

3. El usuario de práctica es `ctf_` seguido del run_id que muestra tu reto. Construye el diccionario de doce candidatas:

   ```bash
   printf 'cociber%02d\n' {1..12} > candidatas.txt
   ```

4. Sustituye `RUN_ID` por el identificador de tu corrida y prueba solamente esa cuenta y servicio:

   ```bash
   hydra -l ctf_RUN_ID -P candidatas.txt -s 2222 -t 2 -f 10.10.30.12 ssh
   ```

5. Con la credencial encontrada, abre SSH a `ctf_RUN_ID@10.10.30.12` usando `-p 2222`. Lee `~/flag.txt` y pega el valor en el campo de la plataforma. La guía no contiene una flag fija.
6. Al resolver, la corrida pasa por limpieza. Comprueba que termina liberada; no sigas usando una cuenta de una corrida cerrada.

## ESC-03 — Investigación SQL en DVWA

**Objetivo:** identificar una entrada vulnerable y recuperar la evidencia de tu corrida. Herramientas: navegador de la Kali y módulo SQL Injection de DVWA.

1. Abre `http://10.10.30.20/dvwa/` **desde Kali**. Usa la cuenta de práctica entregada por el instructor.
2. Selecciona nivel de seguridad Low para el ejercicio y localiza el campo indicado por el módulo.
3. Observa qué devuelve una entrada normal y cómo cambia la respuesta al alterar la estructura de la consulta. Determina el número y tipo de columnas antes de extraer datos.
4. Investiga la tabla `ctf_app_db.secrets`. La condición que identifica tu evidencia es `run_id = 'TU_RUN_ID'`. El esquema nuevo usa la columna `run_id`, no el `id` numérico de la instalación anterior.
5. Recupera únicamente tu columna `flag`, envíala en CoCiber y espera el cierre. Las filas de otras personas y la administración de las VM quedan fuera del ejercicio.
6. Si la víctima pasa a mantenimiento, el instructor debe completar su restauración; reiniciar el navegador no la habilita.

## Escenarios de la siguiente fase

ESC-01, ESC-04 y ESC-05 **no están disponibles para iniciar**. Sus objetivos previstos son reconocimiento de un servicio confirmado, movimiento lateral Windows A→B y recuperación/transferencia controlada de un archivo Samba. Las guías finales del jugador se completarán después de validar esos servicios y sus helpers; consulta el [registro de pendientes](PENDIENTES_ESCENARIOS.md).
