# CoCiber CTF

Plataforma de laboratorios de ciberseguridad en Nutanix: jugadores y grupos, retos con banderas por corrida, acceso mediante Guacamole y limpieza de recursos. La instalación nueva utiliza PostgreSQL y Redis externos.

## Empieza por la documentación

**[Orden de ejecución para la plataforma desplegada](Docs/00_Inicio/01_LEEME_PRIMERO.md)**. Sigue esa guía antes de copiar comandos de otros documentos. Incluye los requisitos, el servidor de destino y el resultado esperado de cada etapa.

El estado confirmado es: plataforma desplegada, conexión a la BD correcta y acceso con `admin_ctf`. Los laboratorios todavía deben prepararse. No hace falta limpiar bases ni inicializar otra vez el esquema para continuar.

| Carpeta | Contenido |
| --- | --- |
| [00_Inicio](Docs/00_Inicio/01_LEEME_PRIMERO.md) | Orden general, acceso SSH, comandos base y topología |
| [01_Plataforma](Docs/01_Plataforma/01_VERIFICAR_PLATAFORMA_EXISTENTE.md) | Verificación, actualización de interfaz, Guacamole e inventario |
| [02_Laboratorios](Docs/02_Laboratorios/01_REQUISITOS_Y_TRANSFERENCIA.md) | Preparación de VM y claves, pruebas, pilotos, grupos y demostración |
| [03_Operacion](Docs/03_Operacion/01_RESTAURACION_SNAPSHOTS.md) | Restauraciones, respaldos y actualizaciones posteriores |
| [04_Pendientes](Docs/04_Pendientes/01_ESTADO_Y_ENTREGABLES.md) | Información pendiente para ESC-01, ESC-04 y ESC-05; siguen deshabilitados |
| [05_Referencia](Docs/05_Referencia/01_INSTALACION_DESDE_CERO.md) | Instalación desde cero, esquema, validación técnica e identidad visual |
| [DocumentacionBD](Docs/DocumentacionBD/01_CREDENCIALES_Y_PREPARACION.md) | Reinicio deliberado de los datos e instalación de BD; fuera del recorrido actual |
| [90_Historico](Docs/90_Historico/00_INDICE_HISTORICO.md) | Documentación de la versión anterior, conservada para consulta |

Los números ordenan los documentos **dentro de cada carpeta**. No ejecutes todas las carpetas de forma consecutiva: `DocumentacionBD`, referencia e histórico son rutas condicionadas; el índice de inicio indica cuándo utilizarlas.

## Ruta y componentes de la instalación actual

El proyecto del servidor web está en **`/ctf-plataform/`**, con esa escritura exacta. El nombre del repositorio local puede ser `ctf-platform`; eso no cambia la ruta remota. Los secretos siguen en `/opt/cociber-secrets`.

| Componente | Ubicación / configuración |
| --- | --- |
| Plataforma | LAB-CTFWEB, `10.10.10.13`; `.env.fresh` |
| PostgreSQL / Redis | LAB-DB-POSTGRES, `10.10.10.14`; servicios nativos |
| Guacamole | LAB-GUAC, `10.10.10.10` |
| API nueva | `backend/ctf`, `ctf.infrastructure.main:app` |
| Interfaz nueva | `frontend/src/fresh` |
| Contenedores | `deploy/docker-compose.fresh.yml`: API y web |
| Cola y limpieza | `deploy/systemd/cociber-fresh-worker.service`: proceso independiente |

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

Ya dentro de LAB-CTFWEB, para consultar el estado:

```bash
cd /ctf-plataform/ || exit 1
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
```

Consulta [acceso y comandos base](Docs/00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md) si no estás familiarizado con SSH, las terminales Linux o los editores.

## Alcance de los escenarios

ESC-02 usa SSH didáctico en LAB-LNXVICT (`10.10.30.12:2222`). ESC-03 usa DVWA en LAB-SRVWEB (`10.10.30.20`). Ambos requieren helpers instalados, una Kali preparada, pruebas y piloto antes de publicar. ESC-01/04/05 continúan pendientes para otra fase.

La consola integrada del reto es SSH. La demostración de DVWA necesita adicionalmente un navegador dentro de Kali con acceso gráfico comprobado. Un resultado TCP correcto en Guacamole no demuestra que las credenciales ni el escritorio funcionen.

La implementación histórica (`backend/app`, `.env`, `docker-compose.prod.yml`) se conserva para compatibilidad y consulta. No combines su Compose ni sus guías de banderas con la instalación nueva. Los paquetes de `labs/demo-vulnerable` y `labs/operacion-condor` son opcionales y no sustituyen el recorrido documentado.
