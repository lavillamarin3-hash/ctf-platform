"""Configura el reto; --apply confirma, sin ese parámetro revierte.

La flag se recibe mediante JSON por stdin o CONDOR_CHALLENGE_FLAG. Nunca se
acepta como argumento de proceso ni se incluye en el informe de salida.
"""
import argparse
import asyncio
import json
import os
import sys

from app.db import make_session_factory
from app.services.condor_catalog import configure, upgrade_terminal


def read_config(args, *, stream=None, environ=None):
    environment = os.environ if environ is None else environ
    if getattr(args, 'terminal_workshop', False):
        if args.config_stdin or not args.portal_url:
            raise ValueError('El taller SSH requiere --terminal-workshop --portal-url; usa la variable privada de entorno si necesitas rotar la flag.')
        return args.portal_url, environment.get('CONDOR_CHALLENGE_FLAG'), args.group
    if args.config_stdin:
        if args.portal_url:
            raise ValueError('Usa --config-stdin o --portal-url, no ambos.')
        try:
            raw = (stream or sys.stdin).read(8193)
            if len(raw) > 8192:
                raise ValueError('La configuración supera el tamaño permitido.')
            config = json.loads(raw)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError('La configuración de entrada debe ser un objeto JSON válido.') from exc
        if (not isinstance(config, dict)
                or set(config) - {'portal_url', 'flag_value', 'group_code'}
                or not all(isinstance(config.get(key), str) for key in ('portal_url', 'flag_value'))
                or not isinstance(config.get('group_code', args.group), str)):
            raise ValueError('La configuración requiere portal_url y flag_value; group_code es opcional.')
        return config['portal_url'], config['flag_value'], config.get('group_code', args.group)
    if not args.portal_url or not environment.get('CONDOR_CHALLENGE_FLAG'):
        raise ValueError('Usa --config-stdin o --portal-url junto con CONDOR_CHALLENGE_FLAG.')
    return args.portal_url, environment['CONDOR_CHALLENGE_FLAG'], args.group


async def main():
    parser = argparse.ArgumentParser(description='Registra Operación Cóndor sin desplegar ni consultar servidores.')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--config-stdin', action='store_true')
    parser.add_argument('--portal-url')
    parser.add_argument('--terminal-workshop', action='store_true',
                        help='Actualiza el reto para SSH en Kali; conserva la flag salvo que se proporcione CONDOR_CHALLENGE_FLAG.')
    parser.add_argument('--group', default='45HY')
    args = parser.parse_args()
    try:
        url, flag, group = read_config(args)
    except ValueError as exc:
        parser.error(str(exc))
    factory = make_session_factory()
    try:
        async with factory() as session:
            try:
                if args.terminal_workshop:
                    result = await upgrade_terminal(session, url, group_code=group, flag_value=flag)
                else:
                    result = await configure(session, url, flag, group_code=group)
                if args.apply:
                    await session.commit()
                else:
                    await session.rollback()
            except ValueError as exc:
                await session.rollback()
                parser.error(str(exc))
            print(json.dumps({'applied': args.apply, **result}, ensure_ascii=False))
    finally:
        await factory.kw['bind'].dispose()


if __name__ == '__main__':
    asyncio.run(main())
