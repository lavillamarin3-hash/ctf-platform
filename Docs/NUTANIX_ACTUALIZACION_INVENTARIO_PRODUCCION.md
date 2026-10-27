# Actualización del inventario Nutanix sin pérdida de datos

Actualización dirigida a administradores de **CoCiber CTF**. No ejecuta cambios en Prism/AHV, Guacamole, MariaDB ni Redis; modifica solamente la ficha de inventario PostgreSQL, cuando se solicita expresamente.

## 1. Entorno de laboratorio

| VLAN | Equipo | Dirección |
| --- | --- | --- |
| 20 | LAB-KALI | 10.10.20.10 |
| 20 | LAB-KALI-PURPLE | 10.10.20.11 |
| 20 | LAB-KALI-BLUE | 10.10.20.12 |
| 30 | LAB-WINVICT-A | 10.10.30.10 |
| 30 | LAB-WINVICT-B | 10.10.30.11 |
| 30 | LAB-LNXVICT | 10.10.30.12 |
| 30 | LAB-SRVWEB | 10.10.30.20 |
| 30 | LAB-SRVFSAD | 10.10.30.21 |

**Importante:** el código de arranque ya tiene este catálogo, pero **no sobrescribe fichas preexistentes**. Las nuevas VMs se registran como `planned` hasta verificarlas.

## 2. Preparación y respaldo

Confirma que tienes autorización administrativa, copia de seguridad PostgreSQL verificable y una ventana sin estudiantes conectados. El procedimiento `reconcile_nutanix_inventory.py` no crea ninguna VM faltante: mostrará `missing` para que la registres con la interfaz.

En el servidor de aplicación, comprueba antes el archivo de producción:

```bash
git status --short
git pull --ff-only origin main
sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml build api
```

## 3. Diagnóstico sin escribir nada

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps api python reconcile_nutanix_inventory.py
```

Lee las secciones `plan` y `blockers`. Las actualizaciones admitidas son **solo**:

- LAB-KALI: `192.168.146.134` -> `10.10.20.10`
- LAB-LNXVICT: `192.168.146.137` -> `10.10.30.12`

Si aparecen duplicados, direcciones ocupadas, datos desconocidos o instancias asignadas, **no apliques cambios**. Resuelve primero la discrepancia con el administrador.

## 4. Aplicación explícita

Una vez respaldado PostgreSQL, con la ventana de mantenimiento confirmada y sin conflictos:

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps api python reconcile_nutanix_inventory.py --apply
```

Las fichas actualizadas quedan en estado `planned`, deliberadamente. No se cambian identificadores de Guacamole, nombres, reservas de AHV ni snapshots. El resto del inventario no se borra ni reemplaza.

## 5. Verificación

1. Comprueba que el backend lista el inventario correcto.
2. Registra manualmente las VMs faltantes desde **Administración > Laboratorios / VMs**; verifica nombre, IP, rol y segmento.
3. En **Apache Guacamole**, verifica conectividad y una sesión **real** SSH/RDP. Una prueba TCP abierta no prueba autenticación.
4. Comprueba que cada VM esté físicamente encendida y que las VLAN permitan únicamente los servicios necesarios.
5. Solo después marca cada VM como **ready** desde la interfaz.
6. Realiza una corrida piloto y verifica generación, validación y limpieza de la bandera.

## 6. Funcionalidades que todavía requieren trabajo/validación en AHV

- Confirmación persistente de autenticación SSH/RDP en Guacamole.
- Cupos efectivos de 6 sesiones simultáneas por Kali y asignación a usuarios.
- Restauración AHV de snapshots con control de propietarios y sesiones activas.
- Aislamiento del reto Operación Cóndor por corrida; actualmente su portal es compartido.
- Instalación real del servicio didáctico SSH y del inyector SQL de DVWA en las VMs.

**Este procedimiento no ejecuta ni promete esas operaciones.** Hasta integrar pruebas en vivo, no se debe anunciar que están completas.
