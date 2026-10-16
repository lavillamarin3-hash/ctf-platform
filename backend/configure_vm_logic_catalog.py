import argparse
import asyncio
import json
from app.db import make_session_factory
from app.services.vm_logic_catalog import configure
from app.services.http_catalog import configure as configure_http


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--group', default='45HY')
    args = parser.parse_args()
    factory = make_session_factory()
    try:
        async with factory() as session:
            http_result = await configure_http(session, group_code=args.group)
            result = await configure(session, group_code=args.group)
            if args.apply:
                await session.commit()
            else:
                await session.rollback()
            print(json.dumps({'applied': args.apply, **result, 'http': http_result}, ensure_ascii=False))
    finally:
        await factory.kw['bind'].dispose()


if __name__ == '__main__':
    asyncio.run(main())
