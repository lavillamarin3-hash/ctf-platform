"""Metadatos de un portal de práctica independiente; nunca realiza peticiones.

La plataforma administra el plazo, las ayudas y la validación de la flag. El
portal tiene su propio proceso y estado compartido: cerrar la corrida no lo
apaga ni promete aislar o restablecer sus datos.
"""
from __future__ import annotations

from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit, urlunsplit


CODE = 'WEB-CONDOR'
SCENARIO = 'CONDOR-WEB-LAB'
STRATEGY = 'external_web_lab'
ASSET_PREFIX = 'CONDOR-PORTAL:'
TERMINAL_ASSET = 'LAB-KALI'
PORT_SCOPE = '18080-18090'
_PRIVATE_NETWORKS = tuple(ip_network(value) for value in (
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', 'fc00::/7'))


def normalize_portal_url(value: str) -> str:
    """Acepta solo destinos explícitos del laboratorio, sin resolver DNS.

    Los dominios públicos, userinfo, parámetros y fragmentos no son necesarios
    para este ejercicio. No se acepta que una URL contenga credenciales.
    """
    if (not isinstance(value, str) or not value or len(value) > 1024
            or any(char.isspace() or ord(char) < 32 for char in value)
            or '\\' in value):
        raise ValueError('La URL del portal de laboratorio no es válida.')
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ValueError('La URL del portal de laboratorio no es válida.') from exc
    if (parts.scheme not in ('http', 'https') or not host
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or '%' in host
            or (port is not None and not 1 <= port <= 65535)):
        raise ValueError('Usa HTTP o HTTPS sin credenciales, parámetros ni fragmentos.')
    host = host.lower()
    if host not in ('localhost', 'condor.lab'):
        try:
            address = ip_address(host)
        except ValueError as exc:
            raise ValueError('El portal debe usar localhost, condor.lab o una IP privada del laboratorio.') from exc
        if not address.is_loopback and not any(
                address.version == network.version and address in network
                for network in _PRIVATE_NETWORKS):
            raise ValueError('El portal debe usar una IP privada o de loopback del laboratorio.')
        host = str(address)
    netloc = f'[{host}]' if ':' in host else host
    if port is not None:
        netloc += f':{port}'
    return urlunsplit((parts.scheme, netloc, parts.path or '/', '', ''))


def supports(challenge) -> bool:
    return challenge.code == CODE and getattr(challenge, 'scenario', None) == SCENARIO


def requires_terminal(challenge) -> bool:
    """La terminal se habilita solo por asignación explícita de Kali."""
    return supports(challenge) and TERMINAL_ASSET in (getattr(challenge, 'asset_references', None) or [])


def normalize_terminal_portal_url(value: str) -> str:
    """El destino SSH debe ser alcanzable desde Kali dentro del alcance dado.

    localhost identificaría a Kali, no al equipo que abrió el navegador. Exigir
    una IP privada literal evita depender de DNS o de archivos hosts externos.
    """
    url = normalize_portal_url(value)
    parts = urlsplit(url)
    try:
        address = ip_address(parts.hostname)
    except ValueError as exc:
        raise ValueError('El taller SSH requiere la IP privada de la víctima; no usa localhost ni nombres DNS.') from exc
    if address.is_loopback:
        raise ValueError('El taller SSH no puede apuntar a localhost o loopback de Kali.')
    if parts.port is None or not 18080 <= parts.port <= 18090:
        raise ValueError('El puerto del taller SSH debe estar dentro de 18080-18090.')
    return url


def portal_url(challenge) -> str:
    if not supports(challenge):
        raise ValueError('El reto no corresponde al portal Operación Cóndor.')
    references = getattr(challenge, 'asset_references', None) or []
    candidates = [reference[len(ASSET_PREFIX):] for reference in references
                  if isinstance(reference, str) and reference.startswith(ASSET_PREFIX)]
    if len(candidates) != 1:
        raise ValueError('El reto requiere una única URL del portal Operación Cóndor.')
    if requires_terminal(challenge):
        return normalize_terminal_portal_url(candidates[0])
    return normalize_portal_url(candidates[0])


def info(run, challenge) -> dict:
    """Datos públicos de navegación, sin contraseña, flag o consultas de red."""
    url = portal_url(challenge)
    host = urlsplit(url).hostname
    if requires_terminal(challenge):
        # El puerto y las rutas son parte del descubrimiento del ejercicio.
        # Se conserva la URL configurada únicamente en el backend.
        return {
            'title': challenge.name,
            'mode': 'vm',
            'terminal_required': True,
            'target_host': host,
            'port_scope': PORT_SCOPE,
            'objective': 'Desde la terminal SSH de Kali descubre el servicio web, adquiere sus artefactos y correlaciona las cuentas con la bitácora para identificar la cuenta adecuada. Usa el diccionario del ejercicio para probar su acceso y publica un comunicado para obtener la flag.',
            'note': 'Trabaja únicamente contra la IP y los puertos indicados. El portal y Kali son compartidos; utiliza la carpeta de tu corrida. Cerrar el reto cierra tu terminal, pero no apaga la web ni reinicia los datos de otros participantes. El tiempo y las pistas se administran en Cociber CTF.',
        }
    try:
        local = host == 'localhost' or ip_address(host).is_loopback
    except ValueError:
        local = False
    mode = 'local' if local else 'vm'
    return {
        'title': challenge.name,
        'portal_url': url,
        'mode': mode,
        'objective': 'Investiga las pistas públicas, consigue acceso al centro de mando y publica un comunicado para recuperar la flag.',
        'note': ('Modo local: abre el portal desde el navegador de este equipo. '
                 if local else 'Abre el portal desde un equipo conectado a la red privada del laboratorio. ')
                + 'El portal es independiente y compartido. Cerrar el reto no apaga la web ni reinicia sus datos. '
                  'El contador y las pistas se administran en Cociber CTF.',
    }
