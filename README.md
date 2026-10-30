# CoCiber CTF

Plataforma web para la operación de retos de ciberseguridad en el laboratorio controlado CoCiber. Gestiona usuarios, grupos, retos, banderas, puntuación, progreso y el acceso del estudiante a la Kali asignada mediante Apache Guacamole.

La plataforma coordina el entrenamiento; no sustituye las funciones de monitoreo y detección de Security Onion ni habilita actividades fuera de los activos y ventanas autorizados.

## Plataforma desplegada

| Componente | Dirección | Responsabilidad |
| --- | --- | --- |
| LAB-CTFWEB | 10.10.10.13 | Frontend Nginx y API FastAPI con Docker Compose. |
| LAB-DB-POSTGRES | 10.10.10.14 | PostgreSQL y Redis nativos para la plataforma. |
| Apache Guacamole | 10.10.10.10 | Espacios de trabajo SSH/RDP de las Kali. |
| LAB-RTRFW | 10.195.20.20 | Salto SSH, router y firewall entre gestión y las VLAN. |

La publicación HTTPS utiliza la IP de gestión 10.195.20.21 con DNAT hacia LAB-CTFWEB. La configuración del proxy TLS debe escuchar en el mismo puerto que publique el firewall. Consulta la [topología Nutanix](./README_TOPOLOGIA_NUTANIX.md) antes de cambiar rutas, interfaces o reglas.

## Demostración vigente

Los dos laboratorios rápidos de la demostración usan una Kali concreta por reto y no dan una consola Guacamole directa a la víctima:

| Reto | Kali del estudiante | Víctima | Alcance de práctica |
| --- | --- | --- | --- |
| ESC-02-BRUTEFORCE | LAB-KALI-BLUE (10.10.20.12) | LAB-LNXVICT (10.10.30.12) | SSH didáctico temporal en 2222. |
| ESC-03-WEBEXPLOIT | LAB-KALI-PURPLE (10.10.20.11) | LAB-SRVWEB (10.10.30.20) | DVWA por HTTP en 80, con fila de bandera temporal. |

La preparación de cuentas técnicas, claves, known_hosts, variables de entorno y overlays de Docker se encuentra en la [guía de banderas](./Docs/GUIA_BANDERAS_LNXVICT_Y_SRVWEB.md).

## Arquitectura de la aplicación

~~~mermaid
flowchart LR
    Browser[Navegador] --> Web[Frontend / Nginx]
    Web --> API[API FastAPI]
    API --> DB[(PostgreSQL)]
    API --> Redis[(Redis)]
    API --> Guac[Apache Guacamole]
    API --> Labs[Servicios didácticos de las VMs]
    Guac --> Kali[Kali asignada]
~~~

El backend aplica control de acceso por roles, valida el estado del reto y crea o elimina únicamente los datos temporales asociados a la corrida. Las claves privadas, contraseñas, banderas y el archivo .env no se versionan.

## Operación

1. Para una instalación nueva, sigue [README-SETUP.md](./README-SETUP.md).
2. Para actualizar una plataforma ya operativa, sigue [GUIA_ACTUALIZAR_PRODUCCION.md](./GUIA_ACTUALIZAR_PRODUCCION.md).
3. Copia el archivo [.env.example](./.env.example) a un .env privado solo en una instalación nueva; nunca sobrescribas un .env de producción.
4. Verifica el Compose y las dependencias antes de recrear API y web:

   ~~~bash
   sudo docker compose -f docker-compose.prod.yml config --quiet
   sudo docker compose -f docker-compose.prod.yml build api web
   sudo docker compose -f docker-compose.prod.yml run --rm --no-deps api python -m app.check_services
   sudo docker compose -f docker-compose.prod.yml up -d --force-recreate --wait api web
   ~~~

Los overlays de secretos de LNXVICT y SRVWEB son opcionales y se habilitan solo después de completar su guía. No uses docker compose down -v, no restaures snapshots durante una corrida y no añadas secretos a Git.

## Documentación útil

- [Topología de red dentro de Nutanix](./README_TOPOLOGIA_NUTANIX.md)
- [Banderas dinámicas de LNXVICT y SRVWEB](./Docs/GUIA_BANDERAS_LNXVICT_Y_SRVWEB.md)
- [Reto SSH desde Kali Blue y Guacamole](./Docs/RETO_SSH_KALI_BLUE_GUACAMOLE_RDP.md)
- [Gestión de formularios, grupos, laboratorios y retos](./Docs/GUIA_FORMULARIOS_GRUPOS_LABS_RETOS_COCIBER.md)
- [Recuperación TLS de Guacamole](./Docs/RECUPERACION_TLS_GUACAMOLE_PRODUCCION.md)
- [Tiempo, pistas y descuento de puntos](./Docs/CONFIGURAR_TIEMPO_Y_PISTAS.md)
- [Operación Cóndor](./Docs/GUIA_OPERACION_CONDOR.md)
- [Eliminar retos](./Docs/ELIMINAR_RETOS.md)
- [Verificación de release](./Docs/VERIFICACION_RELEASE.md)

La documentación interactiva de la API está disponible en /docs solamente en la API interna; el proxy de producción no la expone.
