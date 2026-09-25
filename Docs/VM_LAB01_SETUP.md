# VM víctima LAB-01 · Preparación técnica

Este documento se ejecuta manualmente en la VM víctima `192.168.146.137` por el administrador del laboratorio.

## 1. Confirmar SSH

```bash
ip addr
sudo systemctl status ssh
sudo ss -lntp | grep ':22'
```

## 2. Crear cuenta de servicio

```bash
sudo useradd --create-home --shell /bin/bash ctf-injector
```

La cuenta se utiliza solo para la operación de inyección; el estudiante debe usar su propia cuenta de laboratorio.

## 3. Instalar el script del inyector

Copiar:

```text
backend/app/infrastructure/injection/scripts/linux/ctf-inject-flag.sh
```

a:

```text
/usr/local/sbin/ctf-inject-flag.sh
```

Luego:

```bash
sudo chown root:root /usr/local/sbin/ctf-inject-flag.sh
sudo chmod 0755 /usr/local/sbin/ctf-inject-flag.sh
```

## 4. Crear sudoers mínimo

Ejemplo:

```text
ctf-injector ALL=(root) NOPASSWD: /usr/local/sbin/ctf-inject-flag.sh
```

Validar:

```bash
sudo visudo -c
```

## 5. Preparar árbol CTF

```bash
sudo install -d -o root -g root -m 0755 /opt/ctf
sudo rm -f /opt/ctf/flag.txt
```

No colocar una flag fija definitiva en el archivo.

## 6. Verificar desde el backend

Antes de habilitar `FLAG_INJECTOR_ENABLED=true`, validar que el backend pueda abrir SSH a la VM usando la clave configurada y un `known_hosts` correcto.

## 7. Verificación del inyector

La prueba definitiva debe hacerse desde el backend con el mismo usuario de servicio y script configurados para la aplicación. No utilizar la cuenta Guacamole del estudiante.
