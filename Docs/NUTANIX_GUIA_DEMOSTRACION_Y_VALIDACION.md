# CoCiber CTF: demostración y validación paso a paso

Guía para expositor o estudiante sin experiencia. Usa únicamente la red del laboratorio autorizada. **No hay evidencia de pruebas en vivo contra Nutanix desde esta rama.**

## Preparación de la exposición (administrador)

1. Comprueba que se ven la web de CoCiber y el panel de administración.
2. En **Apache Guacamole**, localiza LAB-KALI (10.10.20.10) y LAB-LNXVICT (10.10.30.12). Pulsa **Verificar conexión**; el resultado **Puerto accesible** significa solo conexión TCP desde la API. Abre la nueva ventana e inicia sesión en Guacamole con la cuenta autorizada. Verifica el escritorio o terminal. Registra por separado **TCP: correcto** y **sesión: correcto**.
3. En la VM víctima verifica con el tutor que el servicio didáctico `2222` está preparado y que el reto `ESC-02-BRUTEFORCE` tiene una flag dinámica activa. Comprueba que no se restaurará el snapshot durante la actividad.
4. Comprueba desde Kali qué puerto HTTP del laboratorio responde en LAB-SRVWEB (10.10.30.20). Anota esa URL en la configuración del reto correspondiente. No muestres credenciales, cookies ni flags en diapositivas.

## Demostración 1: SSH de práctica

1. Abre el reto **ESC-02-BRUTEFORCE** y pulsa **Iniciar ejercicio**.
2. Abre la terminal de **Kali** dentro de CoCiber/Guacamole.
3. Lee el **usuario temporal** y el diccionario de doce contraseñas que proporciona el propio reto.
4. Copia exactamente el comando para guardar la lista de doce candidatas que muestra CoCiber; no uses diccionarios externos.
5. Ejecuta el comando de Hydra que propone el reto, con **un intento concurrente**, exclusivamente contra `10.10.30.12:2222`. Espera el resultado de la contraseña de la cuenta temporal.
6. Conecta al servicio didáctico con `ssh -p 2222 ctf<ID>@10.10.30.12` (sustituye ID por el que se muestra). Introduce la contraseña del laboratorio.
7. En la consola restringida escribe `cat flag.txt`. Copia la evidencia de la corrida al formulario **Validar bandera** y observa el resultado y los puntos.
8. Cierra el reto; prueba que la cuenta temporal ya no se acepta. Ejecuta una nueva corrida y comprueba que la flag es diferente.

**Fallo habitual:** no es válido probar SSH del puerto 22, porque 22 es el servicio administrativo y el objetivo de práctica es 2222.

## Demostración 2: Operación Cóndor

1. En el panel abre **WEB-CONDOR**, consulta IP/puerto autorizado e inicia.
2. Desde Kali observa el servicio HTTP de `10.10.30.20` usando la URL/puerto real de Cóndor. No presupongas un puerto basándote en guías antiguas.
3. Examina las noticias y recursos de práctica, relaciona los registros para encontrar la cuenta con permiso de publicar.
4. Utiliza **únicamente el diccionario acotado** del portal para comprobar las credenciales del formulario web; no pruebes cuentas Linux ni servicios externos.
5. Inicia sesión, redacta un comunicado de auditoría dentro de las longitudes solicitadas y publícalo.
6. Copia la flag presentada en el portal y envíala a la plataforma CoCiber CTF. Verifica puntuación y ranking. Explica al público que, hasta integrar flags dinámicas por corrida, este es un **portal compartido**.
7. Cierra las sesiones en ambos portales. **No restaures LAB-SRVWEB mientras otras personas estén trabajando**.

## Demostración 3: aplicación web vulnerable adicional

**Pendiente de integrar.** Antes de incluirla en el guion, solicita y revisa `33_Fase5_App_Vulnerable_LAB_SRVWEB`, verifica rutas y puertos reales, define la bandera y realiza una prueba manual desde Kali, seguida de una restauración controlada. No se recomienda improvisar una explotación en público.

## Ficha de aceptación del tutor

| Comprobación | Resultado esperado | Estado |
| --- | --- | --- |
| IP correcta | Kali 10.10.20.10 / Linux 10.10.30.12 / web 10.10.30.20 | Por verificar |
| Guacamole TCP | El botón indica puerto abierto | Por verificar |
| Guacamole autenticación | Terminal o escritorio funcional | Por verificar |
| SSH práctica | Se valida una flag única por corrida | Por verificar |
| SSH cierre | Cuenta temporal inaccesible | Por verificar |
| Cóndor | Publicación y flag aceptada por CoCiber | Por verificar |
| Cóndor individual | Cada estudiante obtiene flag distinta | **No implementado** |
| Snapshot AHV | Restaura sin interferir con otras sesiones | Por verificar |
| Seguridad | Sin exposición pública de contraseñas/flags | Por verificar |

Si una fila falla, el expositor no debe afirmar que el ejercicio está operativo.
