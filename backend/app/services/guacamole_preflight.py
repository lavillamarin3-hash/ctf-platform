"""Preflight de conexiones Guacamole contra el inventario autorizado de Nutanix.

El socket abierto demuestra conectividad TCP desde la API, NO autenticación
SSH/RDP ni conectividad desde guacd. El administrador debe probar Guacamole
visualmente antes de habilitar la VM. Nunca probar hosts arbitrarios.
"""
from __future__ import annotations

import asyncio
from ipaddress import ip_address

LAB_TARGETS = {
    "10.10.20.10": "LAB-KALI",
    "10.10.20.11": "LAB-KALI-PURPLE",
    "10.10.20.12": "LAB-KALI-BLUE",
    "10.10.30.10": "LAB-WINVICT-A",
    "10.10.30.11": "LAB-WINVICT-B",
    "10.10.30.12": "LAB-LNXVICT",
    "10.10.30.20": "LAB-SRVWEB",
    "10.10.30.21": "LAB-SRVFSAD",
}
ALLOWED_PORTS = {"ssh": {22, 2222}, "rdp": {3389}}


def connection_target(connection) -> tuple[str, int, str]:
    """Validar el host sin DNS para evitar SSRF desde el panel admin."""
    protocol = str(connection.protocol).lower()
    if protocol not in ALLOWED_PORTS:
        raise ValueError("Solo se admiten conexiones SSH y RDP del laboratorio")
    try:
        host = str(ip_address(str(connection.hostname or "").strip()))
        port = int(connection.port)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("La conexión requiere una IP y puerto válidos") from exc
    if host not in LAB_TARGETS or port not in ALLOWED_PORTS[protocol]:
        raise ValueError("El destino no pertenece al inventario/puerto permitido de Nutanix")
    return host, port, protocol


async def check_connection(connection, timeout: float = 3.0) -> dict:
    host, port, protocol = connection_target(connection)
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await asyncio.wait_for(writer.wait_closed(), timeout=timeout)
    except (OSError, TimeoutError, asyncio.TimeoutError):
        return {"reachable": False, "hostname": host, "port": port,
                "protocol": protocol, "vm_name": LAB_TARGETS[host],
                "message": "No se pudo abrir el puerto desde la API. Revisar VLAN, ACL y servicio."}
    return {"reachable": True, "hostname": host, "port": port,
            "protocol": protocol, "vm_name": LAB_TARGETS[host],
            "message": "Puerto accesible desde la API. Falta verificar el inicio de sesión en Guacamole."}
