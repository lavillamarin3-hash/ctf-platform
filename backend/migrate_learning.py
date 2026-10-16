"""Migración aditiva de ayudas: solo dos tablas, sin backfill ni cambios de puntos."""
import argparse
import asyncio
import json
from sqlalchemy import inspect
from app.db import make_session_factory
from app.models import ChallengeHintReveal, ChallengeLearningProgress

TABLES = (ChallengeLearningProgress.__table__, ChallengeHintReveal.__table__)


def create_tables(connection):
    for table in TABLES:
        table.create(connection, checkfirst=True)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    factory = make_session_factory()
    engine = factory.kw['bind']
    try:
        async with engine.begin() as connection:
            if args.apply:
                await connection.run_sync(create_tables)
            existing = await connection.run_sync(lambda sync: {table.name: inspect(sync).has_table(table.name) for table in TABLES})
        print(json.dumps({'applied': args.apply, 'tables': existing, 'backfill': False}))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
