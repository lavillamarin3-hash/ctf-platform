# ESC-01: guía para preparar la habilitación

**Estado:** configurado como `RECON-SCAN-LAB`, deshabilitado. Víctimas candidatas: LAB-LNXVICT (10.10.30.12) y LAB-SRVWEB (10.10.30.20). Atacante: una Kali libre del inventario. La fase siguiente decidirá el servicio concreto; no se presupone ningún puerto oculto existente.

## 1. Acceder a la víctima que se propone

Desde el equipo de administración:

```bash
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
# O, si se propone LAB-SRVWEB:
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
```

Introduce la contraseña de mantenimiento de forma interactiva. Conserva la sesión abierta mientras haces comprobaciones; no cambies SSH administrativo.

## 2. Identificar estado real, sin instalar nada

```bash
hostname
cat /etc/os-release
ip -br address
ip route
sudo ss -lntup
sudo systemctl list-units --type=service --state=running --no-pager
sudo find /usr/local/sbin -maxdepth 1 -type f -name 'ctf-*' -printf '%f\n'
```

Entrega solo las líneas relacionadas con servicios del laboratorio. Si existe un helper para reconocimiento, anota su ruta y revisa su contenido localmente para confirmar que no incluye claves o flags fijas antes de compartirlo. No exportes `/etc/shadow`, claves SSH privadas ni archivos `.env`.

## 3. Definir el objetivo didáctico

Elige y documenta **una** opción: servicio ya disponible y aislable, o servicio didáctico nuevo pendiente de instalar. Completa:

| Campo | Información a entregar |
| --- | --- |
| Víctima elegida | Nombre e IP confirmados |
| Servicio | Nombre, protocolo, unidad/proceso y puerto real |
| Descubrimiento esperado | Qué identifica el jugador mediante enumeración |
| Evidencia | Banner, respuesta o archivo; ruta exacta sin incluir su contenido |
| Identificador | Cómo seleccionará la evidencia de su run_id |
| Aislamiento | Cómo evita mostrar evidencia de otra corrida |
| Persistencia | Archivos/procesos que create genera y destroy elimina |
| Snapshot | Nombre y fecha del snapshot anterior a la práctica |

No reutilizar el puerto 22 administrativo ni modificar sshd para este reto. Si se propone un puerto nuevo, primero comprueba que no está ocupado y registra la propuesta; todavía no lo abras ni lo publiques.

## 4. Comprobar la ruta desde Kali

En LAB-KALI-BLUE o LAB-KALI-PURPLE, ejecuta:

```bash
ip -br address
ip route
# Comprobar solo la víctima elegida, no todo Nutanix:
ping -c 2 10.10.30.12
```

Una ausencia de respuesta ICMP no demuestra que el servicio esté caído. Con el puerto real ya identificado, comprueba **ese puerto** mediante `nc -vz IP PUERTO` sustituyendo IP y PUERTO por lo registrado. Entrega resultado desde ambas Kali. No hagas pruebas hacia VLAN10: su bloqueo forma parte de la topología.

## 5. Contrato que se implementará después

El helper deberá aceptar `create|check|destroy` y run_id de 12 hex. create recibe la flag por stdin; check devuelve JSON con el hash SHA-256 de la evidencia realmente accesible; destroy elimina solo el recurso de esa corrida y debe aceptar una repetición sin fallar si ya no existe. No leer stdin en check/destroy.

La ruta final del helper se decidirá y registrará tras revisar el servicio; hoy no hay una ruta operativa que se pueda colocar en `.env`. El backend debe permitir únicamente esa ruta y la víctima seleccionada, nunca un comando suministrado por el jugador.

## 6. Evidencias de aceptación de la próxima fase

- create seguido de check devuelve el hash esperado sin revelar la flag en logs.
- Kali descubre y consulta el servicio previsto.
- Una segunda corrida espera en cola y no sobrescribe la primera.
- destroy elimina bandera, proceso y puerto temporal cuando corresponda.
- Repetir destroy no afecta otros servicios; puerto 22 y otros laboratorios siguen operativos.
- Piloto de plataforma, consola y cierre aprobados. Solo entonces se cambia enabled y se publica.
