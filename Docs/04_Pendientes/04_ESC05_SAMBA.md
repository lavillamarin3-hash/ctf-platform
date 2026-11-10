# 04. ESC-05: guía para preparar Samba y exfiltración

**Estado:** `EXFIL-SMB-LAB`, T1048, avanzado, 500 puntos, **deshabilitado**. Víctima: LAB-SRVFSAD, 10.10.30.21. Atacante: Kali asignada por la plataforma. No se presupone nombre de recurso, cuenta de práctica ni contraseña Samba.

## 1. Conectarse por la ruta de administración

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-srvfsad@10.10.30.21
```

Ya dentro de LAB-SRVFSAD, en su terminal Linux:

```bash
hostname
cat /etc/os-release
ip -br address
ip route
```

Si la cuenta de mantenimiento es distinta, registra el nombre real. No modifiques la red para evitar el salto SSH.

## 2. Identificar Samba y recursos

```bash
smbd --version
sudo systemctl status smbd --no-pager
sudo ss -lntup
sudo testparm -s
sudo find /usr/local/sbin -maxdepth 1 -type f -name 'ctf-*' -printf '%f\n'
```

Si `smbd` o la unidad no existen, registra la salida: podría tratarse de otra modalidad de Samba. No instales un servicio diferente para hacer coincidir la guía. Comparte solo la sección del recurso CTF pertinente y los parámetros globales necesarios; revisa que no haya secretos antes de enviarlos.

## 3. Precisar permisos y ruta

Con el recurso real obtenido de testparm, registra:

| Campo | Información necesaria |
| --- | --- |
| Recurso SMB | Nombre exacto; no se asume `ctf` |
| Ruta local | Directorio real y propietario/grupo |
| Acceso | Usuarios permitidos, lectura/escritura, guest permitido o no |
| Cuenta de práctica | Nombre y método de creación, sin contraseña |
| Cuenta técnica | Nombre, SSH por clave y sudo restringido |
| Directorio por corrida | Estructura con run_id de 12 hex |
| Evidencia | Nombre del archivo que guardará la flag de esa corrida |
| Limpieza | Eliminación de usuario Samba, archivo y permisos temporales |

Para la ruta confirmada, usa `stat` y `getfacl` si está disponible. No hagas `chmod -R`, `chown -R` ni habilites guest para «probar rápido».

## 4. Comprobar desde ambas Kali

```bash
nc -vz 10.10.30.21 445
# Sustituye CUENTA_DE_PRACTICA por el nombre validado.
# smbclient pedirá su contraseña de forma interactiva; no usar -U usuario%clave.
smbclient -L //10.10.30.21 -U CUENTA_DE_PRACTICA
```

Entrega el resultado de conectividad y el recurso visible. No pegues contraseñas ni hashes de cuentas Samba. Si las credenciales aún no existen, documenta esa dependencia y omite la autenticación.

## 5. Definir qué significa «exfiltración» en esta demo

El instructor debe decidir si basta con recuperar un archivo por SMB o si el objetivo incluye transferirlo a un receptor controlado. Para la segunda opción, registra receptor, IP, protocolo, puerto y condición de éxito. El receptor debe estar en el laboratorio autorizado; no uses servicios externos ni des por hecho salida a Internet.

VLAN20 y VLAN30 no alcanzan VLAN10. Por tanto, un receptor en la plataforma o en la BD administrativa no es un destino directo válido desde la víctima. No se modificarán reglas para hacerlo funcionar sin un diseño aprobado.

## 6. Contrato del helper pendiente

El helper deberá aceptar create/check/destroy y run_id validado; recibir la flag por stdin; devolver en check su hash SHA-256; y limpiar exclusivamente su directorio/cuenta por corrida. Debe reconocer recursos que él creó y rechazar borrar una cuenta o ruta ajena. Si usa cuentas Samba temporales, la limpieza debe incluir su base de cuentas además del usuario Linux cuando corresponda.

No existe todavía una ruta operativa del helper en el repositorio. Entrega la ruta real si ya está instalado, o solicita su implementación. La fase siguiente incorporará esa ruta a una lista cerrada del adaptador y validará la cuenta labops con sudo restringido.

## 7. Prueba de aceptación futura

Crear evidencia, comprobar hash, autenticar desde la Kali, recuperar solo el archivo de la corrida, enviar la flag y limpiar. Verificar que otra cuenta/corrida no vea el archivo y que destroy sea idempotente. Forzar una caída después de crear el usuario para comprobar compensación. Publicar solo tras un piloto exitoso y la revisión del instructor.
