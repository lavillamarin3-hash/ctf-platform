# 07. Crear jugadores, asignar grupos y publicar tras el piloto

**Antes:** completa [06. Pruebas y worker](06_PRUEBAS_Y_WORKER.md). Se realiza en el navegador, con la URL de la plataforma que ya utilizas y la cuenta `admin_ctf`. No requiere ejecutar comandos SQL ni volver a crear el administrador.

## 1. Revisar que existen los recursos

En **Máquinas** debe figurar disponible al menos una Kali y la víctima del ejercicio. En **Laboratorios** deben estar disponibles `LAB-ATACANTES` y `LAB-VICTIMAS`. En **Retos** deben existir los borradores del [catálogo](../01_Plataforma/04_INVENTARIO_Y_CATALOGO.md). Si faltan, vuelve a esa guía antes de crear duplicados.

| Reto | Víctima | Estrategia | Requisito especial |
| --- | --- | --- | --- |
| ESC-02-BRUTEFORCE | LAB-LNXVICT | SSH-PASSWORD-LAB | SSH didáctico 2222 |
| ESC-03-WEBEXPLOIT | LAB-SRVWEB | DVWA-SQLI-LAB | DVWA y navegador accesible dentro de Kali |

ESC-01, ESC-04 y ESC-05 permanecen deshabilitados. No intentes publicarlos en esta fase.

## 2. Crear las cuentas de demostración

1. Abre **Usuarios** y crea `demo.blue` y `demo.purple` como jugadores, cada uno con una contraseña inicial distinta.
2. Entrega la contraseña en privado. Cada jugador debe entrar una vez y completar el cambio obligatorio de clave antes de la presentación.
3. En **Grupos**, crea el código `CTF-DEMO-2026`, un nombre descriptivo y selecciona los dos jugadores. Si el grupo ya existe, úsalo.

Estas cuentas son de CoCiber. Las cuentas Linux y Guacamole de cada corrida se crean automáticamente; no escribas manualmente `ctf_<run_id>` en Usuarios ni crees usuarios permanentes Guacamole para sustituir esa automatización.

## 3. Asignar y probar un reto por vez

1. En **Retos**, abre ESC-02 y selecciona `CTF-DEMO-2026` en **Grupos**; pulsa **Asignar**. Para conservar varios grupos, selecciónalos conjuntamente antes de guardar.
2. Pulsa **Ejecutar piloto**. Si está deshabilitado, revisa las variables y los pasos de [06](06_PRUEBAS_Y_WORKER.md).
3. Abre **Corridas** y localiza la fila marcada «piloto». Espera a que termine **Liberada**, con resultado **Resuelta**. La cola puede esperar si la víctima o todas las Kali están ocupadas.
4. Regresa al reto y actualiza la vista si hace falta. Debe indicar **Piloto: aprobado y limpio**. Entonces pulsa **Publicar**.
5. Repite con ESC-03 solo si todos sus requisitos están cumplidos.

El piloto comprueba la evidencia y el ciclo de creación/limpieza, incluida la preparación del acceso temporal. No concede puntos. Crear la conexión por API no sustituye la comprobación humana de que la consola se abre; haz un ensayo del jugador antes de la presentación.

## 4. Ensayar el acceso del jugador

Abre una ventana privada del navegador y entra como `demo.blue`. Debe ver únicamente los retos publicados para su grupo. Inicia uno, espera **Activa** y abre la consola dentro del reto. No uses la cuenta administradora como sustituto del jugador.

Sigue la [guía 08](08_DEMO_JUGADORES.md). Para una prueba de acceso sin resolver, pulsa **Cerrar corrida** y espera la limpieza. Una corrida real de DVWA puede dejar la víctima pendiente de restauración; completa [el procedimiento de snapshots](../03_Operacion/01_RESTAURACION_SNAPSHOTS.md) antes de volver a ofrecerla.

## 5. Interpretar los estados sin forzarlos

| Resultado | Acción |
| --- | --- |
| En cola durante mucho tiempo | Revisar worker y disponibilidad de víctima/Kali; una Kali tiene un único cupo |
| Limpiando (`reiniciando`) | Revisar conectividad/helpers/Guacamole; el recurso sigue reservado hasta limpiar |
| Piloto no aprobado | Corregir la causa y volver a ejecutarlo; no publicar mediante SQL |
| Reto invisible para el jugador | Comprobar publicación, grupo asignado y pertenencia del jugador |
| Consola no abre | Revisar sesión SSH real y ruta de guacd; «Probar puerto» no valida credenciales |

Los nombres `demo.blue` y `demo.purple` no fijan una Kali específica. El asignador usa una Kali disponible. Para una demo con una Kali concreta, deja disponibles solamente las preparadas que quieras ofrecer, siempre sin interrumpir corridas activas.

Siguiente: [08. Demostración del jugador](08_DEMO_JUGADORES.md).
