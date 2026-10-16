"""Amplía políticas de ayudas existentes; --check consulta y --apply migra sin backfill."""
from __future__ import annotations

import argparse
import asyncio
import json
import re

from sqlalchemy import inspect, text

from app.db import make_session_factory


REQUIRED_TABLES = ('challenges', 'challenge_learning_progress', 'challenge_hint_reveals')
JSON_COLUMNS = (('challenges', 'learning_policy'),
                ('challenge_learning_progress', 'policy_snapshot'))
PENALTY_CHECK = 'ck_learning_hint_penalty'
PENALTY_EXPRESSION = 'penalty_percent >= 0 AND penalty_percent <= 100'


def inspect_schema(connection):
    """Consulta exclusivamente metadatos; no crea las tablas de ayudas anteriores."""
    inspector = inspect(connection)
    existing = set(inspector.get_table_names())
    columns = {name: [column['name'] for column in inspector.get_columns(name)]
               for name in REQUIRED_TABLES if name in existing}
    checks = (inspector.get_check_constraints('challenge_hint_reveals')
              if 'challenge_hint_reveals' in existing else [])
    return {'missing_tables': [name for name in REQUIRED_TABLES if name not in existing],
            'columns': columns, 'checks': checks}


def _range_check_current(checks):
    # PostgreSQL devuelve paréntesis adicionales en las expresiones inspeccionadas.
    normalize = lambda value: re.sub(r'[\s()\"]', '', value).lower()
    return any(check.get('name') == PENALTY_CHECK
               and normalize(check.get('sqltext') or '') == normalize(PENALTY_EXPRESSION)
               for check in checks)


def migration_statements(state):
    """Plan PG idempotente, de alcance limitado y sin escrituras de datos."""
    if state['missing_tables']:
        raise RuntimeError('Faltan tablas requeridas; ejecuta primero migrate_learning.py: '
                           + ', '.join(state['missing_tables']))
    statements = [f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} JSON'
                  for table, column in JSON_COLUMNS if column not in state['columns'][table]]
    if not _range_check_current(state['checks']):
        statements.extend((
            f'ALTER TABLE challenge_hint_reveals DROP CONSTRAINT IF EXISTS {PENALTY_CHECK}',
            f'ALTER TABLE challenge_hint_reveals ADD CONSTRAINT {PENALTY_CHECK} '
            f'CHECK ({PENALTY_EXPRESSION})',
        ))
    return statements


def apply_migration(connection):
    """El llamante proporciona la transacción; solo PostgreSQL admite este DDL."""
    if connection.dialect.name != 'postgresql':
        raise RuntimeError('Esta migración explícita requiere PostgreSQL.')
    statements = migration_statements(inspect_schema(connection))
    for statement in statements:
        connection.execute(text(statement))
    return len(statements)


def schema_status(connection):
    state = inspect_schema(connection)
    missing = state['missing_tables']
    pending = migration_statements(state) if not missing else []
    return {'ready': not missing and not pending, 'missing_tables': missing,
            'pending_statements': pending, 'backfill': False}


async def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Solo consulta (predeterminado).')
    mode.add_argument('--apply', action='store_true', help='Aplica únicamente la migración de políticas.')
    args = parser.parse_args(argv)
    factory = make_session_factory()
    engine = factory.kw['bind']
    try:
        if args.apply:
            async with engine.begin() as connection:
                count = await connection.run_sync(apply_migration)
                status = await connection.run_sync(schema_status)
        else:
            async with engine.connect() as connection:
                count = 0
                status = await connection.run_sync(schema_status)
        print(json.dumps({'applied': args.apply, 'executed_statements': count, **status}))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
