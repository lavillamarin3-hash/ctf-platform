# Validación local — 16 de octubre de 2026

Cambios desplegados en la API y web de Cociber CTF, `http://localhost:8081/`.
El portal independiente sigue en `http://localhost:8094/`; no se instaló Ubuntu
ni se modificaron las VMs.

- Backend: **290 pruebas aprobadas**, incluida eliminación con roles,
  confirmación, dependencias, rollback y prevención de recreación automática;
  ciclo Cóndor con plazo persistente, acceso por grupo y propietario,
  validación de flag, descuentos y puntos otorgados una sola vez.
- Frontend: build de producción aprobado (**114 módulos**), 33 pruebas MJS
  y los cuatro archivos de regresiones CJS aprobados.
- PostgreSQL real: fixture QA dentro de una transacción exterior. Se verificó
  el borrado del grafo, el rechazo por limpieza pendiente, el rollback de un
  fallo previo al commit y la conservación del otro reto, usuarios, grupos,
  VMs y resultados. Al terminar se revirtió todo y se comprobó que el snapshot
  de tablas y puntos coincidía con el inicial.
- Antes de publicar se guardó un respaldo PostgreSQL fuera del repositorio.
  Tras publicar, los **12 resultados históricos** conservaban sus puntos.
- `WEB-CONDOR` publicado y asignado a **45HY / verde**: 250 puntos, 45 minutos,
  tres pistas del 10 % y finalización asistida al 25 % tras el vencimiento.
  Su hash se comprobó contra la flag privada de la instalación local.
- Navegador: administrador ve la eliminación por reto, los recuentos y la
  confirmación obligatoria. Se canceló la vista previa sin borrar el reto.
  Como estudiante se verificó la asignación, el inicio, el contador de 45
  minutos, las pistas cerradas y el botón que abrió la web en otra pestaña.
  No se revelaron pistas ni se registraron puntos en la cuenta del estudiante.

El editor de Cóndor usa un campo de URL independiente y no exige una VM. El
portal local es compartido; cerrar la corrida no apaga la web ni borra sus
comunicados. Las pruebas de puntuación se hicieron sobre datos aislados,
sin completar el reto por el estudiante real. No se eliminó ningún reto real.

La web independiente conserva su código en el repositorio Operación Cóndor;
esta integración pertenece al repositorio de Cociber CTF. Los cambios de esta
entrega están guardados localmente; no se realizó un nuevo push en esta tarea.
