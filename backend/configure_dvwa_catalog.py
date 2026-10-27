"""Ejecutar bajo el contenedor API con --apply, tras backup y validación de la VM."""
import argparse
import asyncio
import json
from app.db import make_session_factory
from app.services.dvwa_catalog import configure


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--group', required=True)
    args = parser.parse_args()
    factory = make_session_factory()
    try:
        async with factory() as session:
            result = await configure(session, group_code=args.group)
            if args.apply: await session.commit()
            else: await session.rollback()
            print(json.dumps({'applied': args.apply, **result}, ensure_ascii=False))
    finally:
        await factory.kw['bind'].dispose()


if __name__ == '__main__':
    asyncio.run(main())
