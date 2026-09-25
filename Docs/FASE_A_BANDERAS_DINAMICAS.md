# Fase A — base de banderas dinámicas

## Objetivo

Esta fase implementa la base de dominio e infraestructura necesaria para el
sistema de banderas dinámicas sin activar todavía Prism, Guacamole temporal
ni el ciclo completo de inicio/finalización.

## Componentes

```text
backend/app/
├── domain/
│   ├── flags/service.py
│   ├── challenges/strategies.py
│   ├── instances/states.py
│   └── ports/
│       ├── flag_injector.py
│       └── instance_repository.py
├── repositories/
│   └── challenge_instances.py
└── infrastructure/injection/
    ├── ssh.py
    └── scripts/linux/
        ├── ctf-inject-flag.sh
        └── install-ctf-flag-injector.sh
```

## Visual Studio Code

No existe una dependencia runtime de Visual Studio Code. VS Code solo es la
herramienta de edición y diagnóstico. Los scripts se escriben una vez y el
backend los utiliza posteriormente por SSH. Para preparar la VM, Remote SSH
de VS Code es opcional; también puede utilizarse una terminal SSH normal.

## Generación

`FlagService.generar_bandera()` genera una bandera con 16 bytes aleatorios
criptográficamente seguros, con formato:

```text
FLAG{lab-01_<32 caracteres hex>}`
```

El valor en claro está pensado para existir solamente durante el intento.

## VM Linux

1. Copiar `ctf-inject-flag.sh` a la VM víctima.
2. Instalarlo como `/usr/local/sbin/ctf-inject-flag.sh` con propietario root.
3. Crear una cuenta de servicio dedicada.
4. Conceder en sudoers únicamente:

```text
ctf-injector ALL=(root) NOPASSWD: /usr/local/sbin/ctf-inject-flag.sh
```

El script solo acepta rutas dentro de `/opt/ctf/` y no se ejecuta de forma
automática con este commit.

## Variables de entorno

Configurar en `.env` únicamente cuando el laboratorio esté preparado:

```text
FLAG_INJECTOR_ENABLED=true
FLAG_INJECTOR_SSH_USER=ctf-injector
FLAG_INJECTOR_SSH_PRIVATE_KEY=/run/secrets/ctf_injector_ed25519
FLAG_INJECTOR_KNOWN_HOSTS=/run/secrets/known_hosts
FLAG_INJECTOR_SSH_PORT=22
FLAG_INJECTOR_REMOTE_SCRIPT=/usr/local/sbin/ctf-inject-flag.sh
FLAG_INJECTOR_STRICT_HOST_KEY=true
```

El backend no guarda estas credenciales en el repositorio.

## Base de datos

Se agrega `challenge_instances` como pool de instancias reutilizables. La
plataforma existente mantiene sus tablas `challenges`, `users`,
`challenge_runs` y `vm_assets`; no se duplica ese modelo.

El esquema se crea automáticamente mediante `Base.metadata.create_all` y
también existe la migración SQL `migrations/0001_fase_a_dynamic_instances.sql`.

## Aún no implementado en Fase A

- restauración de snapshots mediante Prism Element API v3;
- locks Redis del orquestador;
- asignación efectiva de una instancia al `ChallengeRun`;
- permisos temporales READ en Guacamole;
- revocación y restauración al cerrar;
- worker de timeout;
- endpoint definitivo de `POST /submissions` basado exclusivamente en la instancia.

Esas partes corresponden a las fases posteriores del documento 20.
