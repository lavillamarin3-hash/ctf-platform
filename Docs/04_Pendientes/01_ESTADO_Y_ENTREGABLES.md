# 01. Próxima fase: habilitar ESC-01, ESC-04 y ESC-05

Estado acordado el **8 de noviembre de 2026**: configurar las estrategias, conservarlas **deshabilitadas** y completar su integración en otra fase. No es necesario enviar ahora credenciales ni instalar servicios para cerrar este refactor.

| Reto | Configuración disponible | Estado | Guía para recopilar información |
| --- | --- | --- | --- |
| ESC-01-RECON | RECON-SCAN-LAB · T1046 · básico · 100 puntos · LNXVICT/SRVWEB | Pendiente; enabled=false | [Reconocimiento](02_ESC01_RECONOCIMIENTO.md) |
| ESC-04-LATERAL | LATERAL-SMB-LAB · T1021.002 · avanzado · 500 puntos · WINVICT-A→B | Pendiente; enabled=false | [Windows y WinRM](03_ESC04_WINDOWS.md) |
| ESC-05-EXFIL | EXFIL-SMB-LAB · T1048 · avanzado · 500 puntos · SRVFSAD | Pendiente; enabled=false | [Samba y exfiltración](04_ESC05_SAMBA.md) |

Las estrategias aparecen en el formulario avanzado y permiten guardar un borrador. El backend rechaza piloto, publicación e inicio mientras no exista una implementación validada. `WINRM_INJECTOR_ENABLED=true` por sí solo **no** habilita ESC-04. No se sugiere cambiar `enabled` manualmente para evitar la validación.

## Paquete que se entregará en la fase siguiente

1. Una ficha por escenario con los campos de su guía.
2. Salidas de diagnóstico indicadas, con fecha, nombre de VM y usuario que realizó la comprobación. Ocultar contraseñas, claves privadas, tokens y flags reales.
3. Código del helper, si ya existe, o confirmación de que debe implementarse desde cero.
4. Ruta exacta y permisos del helper, acciones que acepta, ejemplo de entrada/salida **sin secretos** y comportamiento si se repite create/destroy.
5. Estado de snapshot y ventana de pruebas. Restaurar un snapshot se hará manualmente, después de drenar y limpiar corridas.

Los secretos se instalarán directamente en los archivos privados/montajes del servidor; no forman parte de la ficha ni se pegan en el chat.

## Trabajo técnico pendiente

- **ESC01-01:** decidir servicio didáctico y punto exacto donde se recupera la evidencia.
- **ESC01-02:** implementar y verificar helper aislado por run_id y su cleanup.
- **ESC04-01:** validar HTTPS WinRM, certificado, cuenta de servicio y permisos mínimos en A y B.
- **ESC04-02:** definir helper Windows, entrada por stdin y compensación de ambas VM.
- **ESC04-03:** ampliar reservas para una **cadena de dos víctimas**. El esquema actual reserva una víctima por corrida; no representa todavía la reserva atómica A→B.
- **ESC05-01:** confirmar recurso Samba, cuentas de práctica y ruta temporal por corrida.
- **ESC05-02:** definir qué constituye evidencia de exfiltración y el destino controlado autorizado.
- **COMÚN-01:** añadir pruebas de compensación, idempotencia y concurrencia para cada adaptador.
- **COMÚN-02:** probar desde LAB-KALI-BLUE y LAB-KALI-PURPLE, incluido acceso desde la consola Guacamole.
- **COMÚN-03:** ejecutar piloto, verificar limpieza, documentar resultado y recién entonces habilitar/publicar.

No hay despliegues ni cambios de red implícitos en estas guías. Las comprobaciones de red se limitan a las VM indicadas en cada ficha.
