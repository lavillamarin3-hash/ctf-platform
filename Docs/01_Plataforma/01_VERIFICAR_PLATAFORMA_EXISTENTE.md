# 01. Verificar la plataforma que ya está instalada

**Antes:** completa [acceso y comandos base](../00_Inicio/02_ACCESO_Y_COMANDOS_BASE.md). Necesitas SSH a LAB-CTFWEB y acceso web como `admin_ctf`. Esta comprobación no crea usuarios ni modifica bases.

## 1. Entrar y situarse

Desde PowerShell local:

```powershell
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
```

En la sesión Linux:

```bash
hostname
cd /ctf-plataform/ || exit 1
pwd
sudo docker compose version
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml config --quiet
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml ps
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli check
```

Esperado: servicios API y web activos; API saludable; `PostgreSQL y Redis: OK`. Si el servicio API está detenido, no repitas instalación de BD: revisa su error con:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml logs --tail 60 api
```

Revisa los registros localmente y oculta información privada antes de compartirlos. Conserva `.env.fresh` y las credenciales ya funcionales.

## 2. Comprobar el acceso web

Abre la dirección HTTPS que ya utilizaste para entrar a la plataforma. La publicación prevista es `https://10.195.20.21`, pero conserva la URL real configurada si usas un nombre DNS. Entra con `admin_ctf` y confirma que ves el menú administrativo.

El login correcto no demuestra que Guacamole, SSH o DVWA estén preparados. Es normal que las máquinas estén «Por preparar», los retos en borrador y los laboratorios aún no disponibles.

## 3. Saber qué pasos omitir

Con la plataforma funcionando, **no ejecutes** `init-db`, SQL de inicialización, creación de otro administrador, limpieza de PostgreSQL ni `FLUSHDB`. La carpeta DocumentacionBD queda como referencia para una reinstalación deliberada.

Siguiente: [actualizar interfaz y Guacamole](02_ACTUALIZAR_INTERFAZ_Y_GUACAMOLE.md). Si esa revisión ya está instalada, continúa directamente con [verificación de Guacamole](03_GUACAMOLE_Y_CONEXIONES.md).
