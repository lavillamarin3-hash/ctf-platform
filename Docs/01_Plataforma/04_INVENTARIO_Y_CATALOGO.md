# 04. Preparar inventario y borradores

**Antes:** [plataforma verificada](01_VERIFICAR_PLATAFORMA_EXISTENTE.md). Esta etapa crea fichas en la plataforma, no VM en Nutanix. No instala servicios en las víctimas ni publica retos.

## 1. Abrir la terminal del servidor web

Desde PowerShell local: `ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13`. Luego, en Linux:

```bash
cd /ctf-plataform/ || exit 1
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python reconcile_nutanix_inventory.py --fresh
```

El primer comando es un diagnóstico. Revisa que los nombres/IP correspondan a [la topología](../00_Inicio/03_TOPOLOGIA_NUTANIX.md). Si hay una discrepancia, detente; no la fuerces para completar la guía.

## 2. Aplicar las fichas y preparar el catálogo

Cuando el diagnóstico sea correcto:

```bash
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python reconcile_nutanix_inventory.py --fresh --apply
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli configure-catalog
sudo docker compose --env-file .env.fresh -f deploy/docker-compose.fresh.yml exec -T api python -m ctf.infrastructure.cli configure-catalog --apply
```

El catálogo crea solamente lo que falta y conserva lo existente compatible. Debes ver dos laboratorios en preparación y cinco retos en borrador. ESC-01/04/05 siguen deshabilitados; ESC-02/03 requieren los helpers y sus pruebas.

## 3. Revisar en el navegador

Actualiza la plataforma. En **Máquinas** revisa las fichas; en **Laboratorios**, los grupos de atacantes y víctimas; en **Retos**, los borradores. **No marques todavía todas las máquinas como disponibles.** Solo se confirmarán aquellas que completes y compruebes en los siguientes capítulos.

La conciliación usa el catálogo confirmado del repositorio; no consulta la API de Prism ni comprueba servicios remotos. Que una ficha exista no demuestra que esa VM sea alcanzable.

Siguiente: [requisitos y transferencia de archivos](../02_Laboratorios/01_REQUISITOS_Y_TRANSFERENCIA.md).
