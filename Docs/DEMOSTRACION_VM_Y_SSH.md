# Demostración con las máquinas existentes

La aceptación registrada aquí corresponde al catálogo anterior. El lote de [investigación con Kali y LNX-VICT](RETOS_VM_LOGICA.md) incorpora WEB-02, WEB-06, FOR-05 y DFIR-01 como prácticas que requieren adquirir datos desde la víctima y refuerza ESC-07. Su guía detalla la publicación y las comprobaciones propias del nuevo lote.

Kali: `192.168.146.134`. Linux víctima: `192.168.146.137`.

## Qué se demuestra

- LAB-01: terminal de la víctima, lectura de la flag y puntuación.
- ESC-01-RECON: Kali consulta el servicio de evidencia de la víctima en 18081.
- ESC-02-BRUTEFORCE: Kali ejecuta Hydra contra SSH de práctica en 2222; encuentra una contraseña temporal, inicia sesión y obtiene una flag distinta por corrida. Técnica T1110.001.
- Otros 34 ejercicios y DFIR-01: terminal real de Kali para analizar sus evidencias sintéticas. No se convierten los inventarios Windows ni los análisis web en servicios vulnerables reales.

## Recorrido breve

1. Encender Docker, la VM de Guacamole, Kali y LNX-VICT. En Guacamole, comprobar que `guacd` escucha en el puerto 4822. Entrar como estudiante de verde.
2. Abrir ESC-02-BRUTEFORCE e iniciar. Seguir los cuatro comandos mostrados: crear diccionario, ejecutar Hydra, conectar por SSH y leer flag.
3. Enviar flag y cerrar. La cuenta de práctica deja de funcionar.
4. Abrir CRY-01 u otro reto de análisis. Pulsar **Copiar comando para preparar archivos**, pegarlo en Kali y pulsar Enter. Trabajar en `~/ctf/corrida-ID`, validar la respuesta y registrar puntos.
5. Para LAB-01 y ESC-01, cerrar la corrida anterior antes de cambiar: comparten una víctima con reserva exclusiva. La pantalla ofrece el cierre cuando la reserva pertenece al mismo alumno.

La contraseña para conectar la terminal integrada es la cuenta personal de la plataforma/Guacamole. La contraseña que encuentra Hydra pertenece únicamente al ejercicio SSH y no sirve para entrar a la plataforma.

## Implementación y operación

El servicio de práctica usa Paramiko, escucha solo en la IP de la víctima, puerto 2222, y acepta conexiones de Kali. Usa intercambio ECDH compatible con Hydra. No cambia OpenSSH del puerto 22, cuentas del sistema, sudoers ni reglas de red. Sus cuentas son entradas temporales en un directorio privado del usuario de inyección, con contraseña almacenada por hash y caducidad de una hora.

La shell solo responde a `help`, `whoami`, `pwd`, `ls`, `cat flag.txt` y `exit`; no ejecuta órdenes del sistema, abre túneles ni ofrece SFTP. La evidencia se entrega tras autenticarse. Cerrar el reto elimina el registro; una conexión ya abierta también comprueba su vigencia antes de responder. No es acceso general a una cuenta Linux.

El servicio arranca al iniciar un reto, sin privilegios root, y termina tras una hora sin nuevas conexiones. Tras reiniciar la VM, vuelve a arrancar al iniciar una nueva corrida. Si una corrida existente perdió el servicio por reinicio, cerrarla y abrir otra. Paramiko y flock deben estar instalados en la víctima; Hydra y SSH, en Kali. Ambas VMs actuales tienen las dependencias comprobadas.

Kali es una VM compartida: las carpetas separadas por corrida organizan archivos, pero no ofrecen aislamiento entre alumnos que usan la misma cuenta del sistema. Para la exposición usar una cuenta de demostración y una sesión a la vez.

La habilitación conserva puntuaciones e historial y registra configuraciones anteriores en `challenge.vm.enable`. No cambia el esquema de PostgreSQL.

```powershell
Get-Content backend/configure_vm_catalog.py | docker compose exec -T api python -
Get-Content backend/configure_vm_catalog.py | docker compose exec -T api python - --apply
```

La primera orden ensaya y revierte; la segunda confirma. Se rechazan cambios de activos en retos con corridas activas. Después deben sincronizarse los permisos de los grupos asignados con Guacamole usando la operación habitual de asignación/sincronización de grupos. No es necesario recrear alumnos.

La aplicación ahora detecta el 401 de una sesión vencida y vuelve al acceso con una explicación. Una contraseña errónea de Guacamole conserva el formulario de terminal para reintentar.

La terminal detecta el error/cierre del túnel y limita la apertura a 30 segundos. Muestra una opción de reconexión; la API registra solo el tipo de excepción y entrega un error sin URL ni token. Para los espacios de análisis y SSH de práctica, la etiqueta identifica correctamente a Kali. En SSH, Ctrl+V permite el evento de pegado del navegador; después de transferir el texto, la aplicación activa el pegado del terminal Guacamole. El alumno pulsa Enter para ejecutar.

Si Tomcat informa `Creation of WebSocket tunnel to guacd failed: java.net.ConnectException: Connection refused`, comprobar el servicio en la VM de Guacamole. `active (exited)` en un servicio SysV no demuestra que el proceso esté escuchando: comprobar también el puerto. Ejecutar cada línea por separado:

```bash
sudo systemctl status guacd --no-pager -l
sudo ss -ltnp | grep 4822
sudo systemctl restart guacd
```

La configuración de esta VM apunta a `localhost:4822`. No cambiar las credenciales de Kali ni su SSH para corregir un demonio Guacamole detenido.

## Comprobación realizada

185 pruebas de backend aprobadas y compilación TypeScript/Vite correcta. Se comprobó también que un fallo del servidor de terminal entrega un error visible sin filtrar el token a la respuesta o al registro. Prueba PostgreSQL con rollback para los 35 casos de análisis: inicio, acceso autorizado a Kali, selección de conexión SSH y conservación de las evidencias/validación. El destino atacante alternativo se rechazó en estos espacios, que solo permiten su Kali asignada.

Prueba sobre las VMs reales: Hydra ejecutado desde Kali contra la cuenta temporal de LNX-VICT, incluyendo el caso de contraseña en la posición 12 del diccionario. Se comprobó autenticación incorrecta rechazada, autenticación correcta, lectura de la flag, puntuación una sola vez y acceso rechazado después del cierre. Los usuarios y puntos de QA se revirtieron y se eliminaron sus cuentas temporales del servicio.

Aceptación visual del 14 de octubre de 2026 con la sesión personal del alumno: ESC-02-BRUTEFORCE abrió Kali y `pwd` respondió `/home/kali`. CRY-01 abrió su terminal, el comando mostrado se pegó y preparó archivos en `/home/kali/ctf/corrida-376`; se comprobó su listado. No se enviaron respuestas ni se añadieron puntos al alumno durante esta aceptación. El error del servidor se resolvió reiniciando `guacd`, que antes figuraba `active (exited)` sin escuchar y después escuchó en `127.0.0.1:4822`.
