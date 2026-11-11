# 12. Validación de Windows/FTP e integración con CoCiber

Completa [10. Windows](10_WINDOWS_A_Y_B.md) y [11. FTP](11_SRVFSAD_FTP.md). La ejecución de comandos debe acreditarse en las VM: las comprobaciones de sintaxis del repositorio no equivalen a una prueba remota.

## 1. Registrar el resultado de la preparación

| Prueba | Resultado requerido | Registrar |
| --- | --- | --- |
| Kali → A:22 | Login como ctf_win_demo, sin ser administrador | Fecha, Kali e identidad de A |
| A → B:445 | Autenticación explícita y lectura de evidencia.txt | Nombre real de B y recurso COCIBER_DEMO |
| Kali → B:445 directo | Bloqueado cuando el diseño exige pasar por A | Resultado y reglas efectivas |
| Kali → SRVFSAD:21 y datos pasivos | Descarga correcta y hash coincidente | Kali, puertos y hash del archivo de prueba |
| Cuenta FTP por SSH | Autenticación rechazada | Resultado de la prueba |
| Cierre | Sesiones cerradas, cuentas de ensayo deshabilitadas y FTP detenido | Responsable y hora |

No incluyas contraseñas, claves privadas ni archivos `.env` en la ficha. Si una prueba falla, conserva su error y corrige ese punto antes de dar la VM por preparada.

## 2. Qué puede comprobarse en la plataforma ahora

En **Guacamole**, el administrador puede consultar o crear conexiones SSH/RDP del catálogo y probar su puerto. Para Windows RDP necesita un servicio RDP y una cuenta autorizada ya configurados; la guía 10 instala SSH en A y no activa RDP. Un puerto abierto no acredita autenticación ni completa el reto.

Las VM Windows y SRVFSAD pueden estar inventariadas, pero deben permanecer **Por preparar/En mantenimiento** para la asignación automática de estos escenarios. Conserva operativos los retos SSH/DVWA ya verificados. No ejecutes la conciliación como sustituto de una prueba de servicio.

## 3. Desarrollo que falta para publicar ESC-04

- Reservar A y B de forma atómica; el modelo actual reserva solo una víctima por corrida.
- Implementar helpers Windows create/check/destroy con run_id de 12 hex, cuentas y archivos exclusivos y flag por entrada estándar; no usar comandos con secretos en argumentos.
- Definir transporte de administración verificado (el adaptador WinRM actual es un punto de extensión, no una implementación). SSH didáctico en A no lo reemplaza automáticamente.
- Verificar identidad/certificado del transporte y permisos limitados de la cuenta técnica.
- Compensar y liberar ambas VM solo después de limpiar cuentas, sesiones, recursos y permisos en las dos.
- Probar fallos entre preparación de A y B, restauraciones y reintentos. Después ejecutar piloto y revisar el recorrido real antes de publicar.

`WINRM_INJECTOR_ENABLED` debe continuar false. Cambiarlo no implementa esas operaciones.

## 4. Desarrollo que falta para publicar ESC-05 por FTP

La petición actual reemplaza Samba por FTP en LAB-SRVFSAD. El catálogo existente todavía contiene `EXFIL-SMB-LAB`; ese identificador continúa deshabilitado.

Debe añadirse una estrategia FTP explícita (nombre propuesto `EXFIL-FTP-LAB`, **todavía no aceptado por el backend**), su helper y una actualización revisada del borrador existente. El helper tendrá que crear una cuenta y raíz FTP por corrida, recibir la flag por stdin, devolver únicamente su SHA-256 en check y retirar todos sus recursos en destroy. Se comprobarán aislamiento, descarga pasiva, revocación, limpieza idempotente y compensación de fallos antes de habilitar el piloto.

Las cuentas manuales de estas guías no deben convertirse en cuentas compartidas entre corridas. Tampoco se debe presentar una bandera estática como si fuera la evidencia dinámica del usuario.

## 5. ESC-01: reconocimiento pendiente

Desde Kali se puede practicar enumeración limitada de los servicios preparados:

```bash
nmap -Pn -sV -p 22 10.10.30.10
nmap -Pn -sV -p 21 10.10.30.21
```

Eso acredita conectividad y reconocimiento de servicio, no entrega una flag dinámica ni habilita ESC-01. Su catálogo actual propone LNXVICT/SRVWEB como víctimas; cambiar a Windows/FTP requiere revisar estrategia y contrato. Sigue la [ficha de reconocimiento](../04_Pendientes/02_ESC01_RECONOCIMIENTO.md) para definir la evidencia antes de publicarlo.

## 6. Ficha que debe conservar el instructor

Anota versión/build de cada SO, pertenencia a dominio/grupo de trabajo, nombres e IP, snapshot previo, servicios/puertos, cuentas de prueba por nombre, ACL/reglas creadas, resultados de la tabla, limpieza y diferencias encontradas. Esa ficha permite implementar los adaptadores con datos reales y evita repetir la preparación del laboratorio.
