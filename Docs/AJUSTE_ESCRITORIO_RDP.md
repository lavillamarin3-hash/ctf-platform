# Escritorio RDP completo

El escritorio se ajusta al espacio de la conexión conservando sus proporciones.
Al entrar o salir de pantalla completa se envían las nuevas dimensiones a
Guacamole. La vista queda centrada y el botón **Ajustar** restaura la vista
completa incluso cuando el zoom ya estaba en su valor inicial.

Para las VMs del laboratorio, Guacamole necesita `resize-method: reconnect`.
Sin ese parámetro ignora los cambios de tamaño y conserva la resolución
estrecha del panel inicial. La reconexión es interna a RDP; no cierra la corrida.
Las conexiones nuevas de tipo RDP reciben este valor si no tienen otro método
explícito. SSH conserva su comportamiento.

Para adaptar las conexiones existentes, desde el backend con su configuración
de Guacamole disponible:

```bash
python configure_rdp_display.py --check
python configure_rdp_display.py --apply
```

El script limita los cambios a RDP de `192.168.146.134` y `192.168.146.137`,
conserva credenciales y atributos, y elimina dimensiones fijas `width`/`height`.
No concede permisos de acceso. Después de aplicarlo, recarga la plataforma y
abre de nuevo RDP para utilizar la nueva configuración.

Referencia: [parámetros de pantalla de Apache Guacamole](https://guacamole.apache.org/doc/gug/configuring-guacamole.html#display-settings).

Comprobado: compilación TypeScript/Vite, cinco pruebas de escala y 194 pruebas
del backend. Con la sesión personal del estudiante, Kali respondió primero a
900×600 y después a 1280×720 al recibir el cambio de tamaño.
