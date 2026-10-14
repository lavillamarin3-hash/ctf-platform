import argparse
import asyncio
import json
from app.db import make_session_factory
from app.services.vm_catalog import configure

async def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--apply',action='store_true'); args=parser.parse_args()
    factory=make_session_factory()
    async with factory() as session:
        result=await configure(session)
        if args.apply: await session.commit()
        else: await session.rollback()
        print(json.dumps({'applied':args.apply,**result}))
    await factory.kw['bind'].dispose()

if __name__=='__main__': asyncio.run(main())
