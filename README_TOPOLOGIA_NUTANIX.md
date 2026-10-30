# Topología de red del laboratorio CoCiber en Nutanix

Este documento describe la topología operativa del laboratorio AHV/Nutanix. Es la referencia para acceso, enrutamiento y demostración de los dos retos piloto. No contiene contraseñas, banderas ni claves privadas.

## Segmentos y equipos

| Zona | Red | Activos principales |
| --- | --- | --- |
| Gestión Nutanix | 10.195.20.0/24 | Equipo del operador, Prism y LAB-RTRFW en 10.195.20.20. |
| VLAN 10 — Administración | 10.10.10.0/24 | Guacamole .10, LAB-CTFWEB .13, LAB-DB-POSTGRES .14. |
| VLAN 20 — Atacantes | 10.10.20.0/24 | LAB-KALI .10, LAB-KALI-PURPLE .11, LAB-KALI-BLUE .12. |
| VLAN 30 — Víctimas | 10.10.30.0/24 | LAB-WINVICT-A .10, LAB-WINVICT-B .11, LAB-LNXVICT .12, LAB-SRVWEB .20, LAB-SRVFSAD .21. |

LAB-RTRFW conecta los cuatro segmentos. Sus interfaces de referencia son ens9 hacia gestión, ens3 hacia VLAN 10, ens4 hacia VLAN 20 y ens5 hacia VLAN 30. Las direcciones de puerta de enlace de las VLAN se administran en el router; no se deben inventar rutas directas desde la red de gestión.

~~~mermaid
flowchart LR
    OP[Operador / red de gestión<br/>10.195.20.0/24]
    PRISM[Prism / Nutanix]
    FW[LAB-RTRFW<br/>10.195.20.20<br/>router y firewall]
    PUB[IP publicada CTF<br/>10.195.20.21:443]

    subgraph V10[VLAN 10 · Administración · 10.10.10.0/24]
        CTF[LAB-CTFWEB<br/>10.10.10.13]
        DB[LAB-DB-POSTGRES<br/>10.10.10.14]
        G[Guacamole<br/>10.10.10.10]
    end
    subgraph V20[VLAN 20 · Atacantes · 10.10.20.0/24]
        PURPLE[LAB-KALI-PURPLE<br/>10.10.20.11]
        BLUE[LAB-KALI-BLUE<br/>10.10.20.12]
    end
    subgraph V30[VLAN 30 · Víctimas · 10.10.30.0/24]
        LNX[LAB-LNXVICT<br/>10.10.30.12]
        WEB[LAB-SRVWEB<br/>10.10.30.20]
    end

    OP --> FW
    PRISM --- OP
    PUB --> FW
    FW --> CTF
    FW --> G
    FW --> BLUE
    FW --> PURPLE
    FW --> LNX
    FW --> WEB
    CTF --> DB
    G --> BLUE
    G --> PURPLE
    BLUE -->|ESC-02 · SSH 2222| LNX
    PURPLE -->|ESC-03 · HTTP 80 /dvwa| WEB
~~~

## Flujo de acceso administrativo

La red de gestión no accede directamente a VLAN 20 ni VLAN 30. El acceso de mantenimiento usa a LAB-RTRFW como salto SSH:

~~~powershell
ssh -J lab-rtrfw@10.195.20.20 lab-lnxvict@10.10.30.12
ssh -J lab-rtrfw@10.195.20.20 lab-srvweb@10.10.30.20
ssh -J lab-rtrfw@10.195.20.20 lab-ctfweb@10.10.10.13
~~~

El segundo salto se origina en el router. Por tanto, las VMs destino registran la procedencia del router y no la del equipo local. Usa cuentas autorizadas y credenciales introducidas de forma interactiva; no incluyas contraseñas en comandos, scripts, capturas ni archivos del repositorio.

## Política de encaminamiento y publicación

La configuración de nftables del router define los siguientes límites:

| Origen | Destino | Regla operativa |
| --- | --- | --- |
| Gestión 10.195.20.0/24 | LAB-RTRFW | SSH administrativo al router. |
| Gestión autorizada | 10.195.20.21:443 | DNAT a LAB-CTFWEB 10.10.10.13:443. |
| VLAN 10 | VLAN 20 y VLAN 30 | Permitido para servicios de plataforma y administración definida. |
| VLAN 20 | VLAN 30 | Permitido por el router; el servicio de cada reto restringe el alcance real. |
| VLAN 30 | VLAN 20 | Permitido para tráfico de respuesta o prácticas explícitamente configuradas. |

La publicación HTTPS depende de que un proxy TLS escuche realmente en LAB-CTFWEB:443. Si el servicio web interno escucha en otro puerto, se debe ajustar el proxy o la regla DNAT de forma coordinada; no se deben abrir puertos temporales como sustituto.

## Flujos de los laboratorios piloto

| Reto | Origen autorizado | Destino | Control adicional |
| --- | --- | --- | --- |
| ESC-02-BRUTEFORCE | Blue 10.10.20.12 | LNXVICT 10.10.30.12:2222 | El servicio SSH didáctico es temporal y acepta solo la Kali Blue. El SSH administrativo en 22 queda fuera del reto. |
| ESC-03-WEBEXPLOIT | Purple 10.10.20.11 | SRVWEB 10.10.30.20:80/dvwa | DVWA usa una fila temporal por corrida; la API accede con una cuenta técnica por SSH con clave. |

Guacamole entrega una sesión sobre la Kali que corresponde al reto y cuyo usuario tenga permiso READ. No se publica una sesión Guacamole privilegiada directamente sobre LNXVICT ni SRVWEB.

## Checklist antes de una demostración

1. Confirma que las cuatro VM del piloto están ready y que el inventario de la plataforma coincide con sus nombres e IPs.
2. Comprueba la sesión de Guacamole de Blue y Purple con una cuenta de prueba.
3. Verifica que 10.195.20.21:443 llega al proxy TLS configurado en CTFWEB.
4. Comprueba que los secretos de las cuentas técnicas están fuera de Git y que los dos overlays de laboratorio están deshabilitados hasta necesitarlos.
5. Publica cada reto solo para el grupo de demostración y ejecuta una corrida por vez.

La [guía de banderas de LNXVICT y SRVWEB](./Docs/GUIA_BANDERAS_LNXVICT_Y_SRVWEB.md) contiene la preparación de las VMs y las variables de entorno. El [README principal](./README.md) describe el despliegue de la aplicación.
