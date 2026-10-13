"""Ejecutar con PYTHONPATH=/app dentro de la API. Sin --apply hace rollback."""
import argparse
import asyncio
import json
from app.db import make_session_factory
from app.services.offline_catalog import configure


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    factory = make_session_factory()
    async with factory() as session:
        report = await configure(session, args.group)
        if args.apply:
            await session.commit()
        else:
            await session.rollback()
        print(json.dumps({'applied': args.apply, **report}, ensure_ascii=False, indent=2))
    await factory.kw['bind'].dispose()


if __name__ == '__main__':
    asyncio.run(main())
