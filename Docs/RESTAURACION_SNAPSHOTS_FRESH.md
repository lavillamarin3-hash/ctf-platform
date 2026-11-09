# Restauración manual de snapshots

La restauración pertenece al encargado de Nutanix. La plataforma no llama a una API de restauración de Prism.

1. **Drenar:** marca la VM en mantenimiento. No se asignan nuevas corridas; las actuales siguen siendo responsabilidad del worker. DVWA queda dirty tras una corrida real por política conservadora.
2. **Cerrar:** en Corridas, solicita cierre de las sesiones afectadas y espera a que estén liberadas. `reiniciando` indica limpieza pendiente, no un permiso para restaurar.
3. **Registrar:** anota VM, motivo, snapshot previo y responsable. El nombre propuesto `LAB-<VM>-PRELAB-<fecha>` es una convención; selecciona el snapshot que realmente existe en Prism.
4. **Restaurar:** el encargado verifica de nuevo que no haya sesiones vivas y restaura manualmente desde la consola de Prism. El procedimiento exacto depende de la versión instalada; no se han inventado endpoints ni automatizaciones.
5. **Comprobar:** desde administración valida IP, servicio de SSH, clave de host y presencia de los helpers. Una restauración puede revertir claves o scripts: compara huellas, no desactives known_hosts para ocultar la diferencia.
6. **Probar:** ejecuta `scripts/probar_inyector.sh` con la VM y estrategia confirmadas. Solo una secuencia create/check/destroy exitosa acredita la prueba; la ficha permanece en mantenimiento.
7. **Confirmar:** el administrador confirma el registro en Mantenimiento. La API exige que la prueba haya pasado y que no existan corridas vivas; después la VM vuelve a ready.

PostgreSQL, Redis y Guacamole residen fuera de la víctima. Un snapshot de la víctima **no** revierte sus reservas, usuarios Guacamole ni puntuaciones. Por eso se cierra y limpia primero en la plataforma.

Para Windows A→B la siguiente fase debe drenar y reservar ambas VM. No se ha habilitado ese escenario mientras falta esa coordinación.
