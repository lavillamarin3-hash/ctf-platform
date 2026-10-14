"""Adaptar solo los escritorios RDP del laboratorio, conservando su configuración.

Sin argumentos o con --check, únicamente consulta. --apply es necesario para
establecer resize-method=reconnect y quitar las dimensiones fijas width/height.
La salida contiene solo el host y los parámetros de resolución, nunca secretos.
"""
import argparse
import asyncio
import json
import sys
from urllib.parse import quote
from app.guacamole import GuacamoleApiError, make_guacamole_admin


LAB_HOSTS = frozenset(('192.168.146.134', '192.168.146.137'))


async def configure(admin, *, apply=False):
    request = getattr(admin, '_api_request', None)
    if not callable(request):
        raise RuntimeError('Se requiere el adaptador real de Guacamole')
    connections = await request('GET', '/connections')
    if not isinstance(connections, dict):
        raise GuacamoleApiError('No se pudieron consultar las conexiones', 502)
    result = []
    for identifier, summary in connections.items():
        if not isinstance(summary, dict):
            continue
        if summary.get('protocol') and str(summary['protocol']).lower() != 'rdp':
            continue
        path = '/connections/' + quote(str(identifier), safe='')
        detail = await request('GET', path)
        if not isinstance(detail, dict):
            raise GuacamoleApiError('No se pudo conservar el detalle de la conexión', 502)
        current = dict(summary)
        current.update(detail)
        if str(current.get('protocol', '')).lower() != 'rdp':
            continue
        official_parameters = await request('GET', path + '/parameters')
        if not isinstance(official_parameters, dict):
            raise GuacamoleApiError('No se pudieron conservar los parámetros de la conexión', 502)
        parameters = dict(current.get('parameters') or {})
        parameters.update(official_parameters)
        host = parameters.get('hostname')
        if host not in LAB_HOSTS:
            continue
        # Requerir los atributos evita enviar un PUT parcial que los borre.
        if not isinstance(current.get('attributes'), dict):
            raise GuacamoleApiError('No se pudieron conservar los atributos de la conexión', 502)
        updated = dict(parameters)
        updated['resize-method'] = 'reconnect'
        updated.pop('width', None)
        updated.pop('height', None)
        if apply and updated != parameters:
            body = dict(current)
            body['identifier'] = str(identifier)
            body['parameters'] = updated
            await request('PUT', path, data=body)
        visible = updated if apply else parameters
        result.append({'host': host, 'resize_method': visible.get('resize-method'),
                       'width': visible.get('width'), 'height': visible.get('height')})
    return result


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Consultar sin modificar conexiones (predeterminado)')
    mode.add_argument('--apply', action='store_true', help='Aplicar el ajuste a los dos hosts RDP del laboratorio')
    args = parser.parse_args()
    try:
        result = await configure(make_guacamole_admin(), apply=args.apply)
    except Exception as exc:
        # No imprimir str(exc), cuerpos HTTP ni URLs que puedan contener tokens.
        status = getattr(exc, 'status_code', None)
        label = type(exc).__name__
        if isinstance(status, int):
            label += f' HTTP {status}'
        print('No se pudo configurar la resolución RDP: ' + label, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
