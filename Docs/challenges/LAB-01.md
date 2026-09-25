# LAB-01 · Reconocimiento SSH controlado

## Propósito

Primer reto funcional del laboratorio real. El estudiante identifica el servicio SSH de la VM víctima, accede por el entorno autorizado y localiza la evidencia dinámica en `/opt/ctf/flag.txt`.

## Activos

- Máquina víctima: `LAB-LNXVICT`
- IP víctima: `192.168.146.137`
- Máquina atacante: `192.168.146.134`
- Guacamole: `192.168.146.132:8080`
- Protocolo de acceso: SSH

## Flag

Modo: `dynamic`.

Plantilla recomendada:

```text
FLAG{lab-01_{{USER}}_{{RUN_ID}}_{{RAND}}}
```

Variables disponibles: `{{CODE}}`, `{{USER}}`, `{{RUN_ID}}`, `{{RAND}}`.

El valor en claro se genera solo durante el inicio del `ChallengeRun`. PostgreSQL conserva únicamente el hash y la huella HMAC de la flag de esa ejecución.

## Archivo de evidencia

Por defecto:

```text
/opt/ctf/flag.txt
```

La ruta se controla desde `FLAG_INJECTOR_FLAG_PATH` y el adaptador remoto solo permite el árbol `/opt/ctf`.

## Flujo técnico

```text
Jugador
  -> POST /challenges/LAB-01/start
  -> validación de asignación al grupo
  -> lock Redis por 192.168.146.137
  -> crear ChallengeRun
  -> generar flag dinámica
  -> SSH con ctf-injector
  -> sudo -n ctf-inject-flag.sh --path ... --flag ...
  -> registrar hash/fingerprint en ChallengeRunFlag
  -> entregar conexión Guacamole
  -> estudiante trabaja
  -> POST /challenges/LAB-01/submissions
  -> comparar contra hash de SU ejecución
  -> cerrar sesión
  -> revocar Guacamole
  -> limpiar /opt/ctf/flag.txt
  -> liberar lock Redis
```

## Requisitos en la VM víctima

1. SSH activo en puerto 22.
2. Usuario de servicio dedicado `ctf-injector`.
3. El usuario de servicio debe poder ejecutar mediante sudo, sin contraseña, únicamente el script del inyector.
4. Debe estar instalado `/usr/local/sbin/ctf-inject-flag.sh`.
5. La cuenta del estudiante no debe ser la cuenta del inyector.
6. El backend debe poder validar la clave del host de la VM cuando `FLAG_INJECTOR_STRICT_HOST_KEY=true`.
7. El usuario remoto necesita acceso de lectura al archivo de flag para que el reto pueda resolverse.

## Configuración del backend

Ejemplo en `.env` local del backend:

```dotenv
FLAG_INJECTOR_ENABLED=true
FLAG_INJECTOR_SSH_USER=ctf-injector
FLAG_INJECTOR_SSH_PRIVATE_KEY=/run/secrets/ctf_injector_ed25519
FLAG_INJECTOR_KNOWN_HOSTS=/run/secrets/known_hosts
FLAG_INJECTOR_SSH_PORT=22
FLAG_INJECTOR_CONNECT_TIMEOUT=10
FLAG_INJECTOR_COMMAND_TIMEOUT=15
FLAG_INJECTOR_STRICT_HOST_KEY=true
FLAG_INJECTOR_REMOTE_SCRIPT=/usr/local/sbin/ctf-inject-flag.sh
FLAG_INJECTOR_FLAG_PATH=/opt/ctf/flag.txt
FLAG_INJECTOR_LOCK_TTL_SECONDS=5400
```

No guardar credenciales ni claves privadas en el repositorio.

## Configuración desde Administración

En `Retos > LAB-01`:

1. Seleccionar la VM `LAB-LNXVICT`.
2. Mantener publicada la prueba para el grupo del `Estudiante 1`.
3. Convertir la flag activa a `Dinámica por ejecución`.
4. Usar la plantilla anterior.
5. Mantener `Orden = 1`.
6. Guardar.

No usar una flag estática para esta prueba.

## Prueba con Estudiante 1

1. Ingresar como Estudiante 1.
2. Abrir `Retos` y seleccionar `LAB-01`.
3. Pulsar `Abrir máquina asignada`.
4. Verificar que la conexión apunta a la VM/SSH correctos.
5. Dentro de la VM, localizar `/opt/ctf/flag.txt`.
6. Enviar la flag a través del formulario del reto.
7. Confirmar que el backend responde `Flag correcta` y registra los puntos al completar el reto.
8. Ir a `Laboratorio > Mis conexiones` y pulsar `Cerrar sesión y limpiar VM`.
9. Verificar en la VM que `/opt/ctf/flag.txt` ya no existe.

## Prueba de aislamiento

Con la VM única actual no se permite una segunda ejecución concurrente. El segundo jugador debe recibir un conflicto indicando que la VM está ocupada. Esto es intencional en esta fase.

La siguiente evolución será sustituir este lock por un pool de `ChallengeInstance` y restauración de snapshot por instancia.
