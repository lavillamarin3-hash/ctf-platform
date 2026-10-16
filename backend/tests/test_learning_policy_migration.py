"""DDL de políticas y datos históricos; SQLite local y conexión PostgreSQL simulada."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.models import (Base, Challenge, ChallengeHintReveal, ChallengeLearningProgress,
                        ChallengeCompletion, User)
from migrate_learning_policy import (PENALTY_CHECK, PENALTY_EXPRESSION, apply_migration,
                                     inspect_schema, migration_statements, schema_status)


def legacy_state():
    return {'missing_tables': [],
            'columns': {'challenges': ['id'], 'challenge_learning_progress': ['id'],
                        'challenge_hint_reveals': ['id', 'penalty_percent']},
            'checks': [{'name': PENALTY_CHECK, 'sqltext': 'penalty_percent = 10'}]}


class LearningPolicyMigrationPlanTests(unittest.TestCase):
    def test_plan_adds_nullable_json_and_replaces_only_the_penalty_check(self):
        plan = migration_statements(legacy_state())
        self.assertEqual(plan, [
            'ALTER TABLE challenges ADD COLUMN IF NOT EXISTS learning_policy JSON',
            'ALTER TABLE challenge_learning_progress ADD COLUMN IF NOT EXISTS policy_snapshot JSON',
            f'ALTER TABLE challenge_hint_reveals DROP CONSTRAINT IF EXISTS {PENALTY_CHECK}',
            f'ALTER TABLE challenge_hint_reveals ADD CONSTRAINT {PENALTY_CHECK} CHECK ({PENALTY_EXPRESSION})',
        ])
        for statement in plan:
            self.assertNotIn('UPDATE', statement)
            self.assertNotIn('DELETE', statement)
            self.assertNotIn('INSERT', statement)
            self.assertNotIn('DEFAULT', statement)
            self.assertNotIn('challenge_completions', statement)

    def test_current_schema_is_noop_and_missing_constraint_is_repaired(self):
        state = legacy_state()
        state['columns']['challenges'].append('learning_policy')
        state['columns']['challenge_learning_progress'].append('policy_snapshot')
        state['checks'] = [{'name': PENALTY_CHECK,
                            'sqltext': '((penalty_percent >= 0) AND (penalty_percent <= 100))'}]
        self.assertEqual(migration_statements(state), [])
        state['checks'] = []
        self.assertEqual(len(migration_statements(state)), 2)

    def test_missing_learning_tables_do_not_create_a_schema(self):
        state = legacy_state()
        state['missing_tables'] = ['challenge_learning_progress', 'challenge_hint_reveals']
        with self.assertRaisesRegex(RuntimeError, 'migrate_learning.py'):
            migration_statements(state)
        with patch('migrate_learning_policy.inspect_schema', return_value=state):
            connection = Mock()
            status = schema_status(connection)
        self.assertFalse(status['ready'])
        self.assertEqual(status['missing_tables'], state['missing_tables'])
        connection.execute.assert_not_called()

    def test_apply_uses_pg_ddl_without_data_writes_and_repeat_is_noop(self):
        state = legacy_state()
        connection = Mock(dialect=SimpleNamespace(name='postgresql'))

        def execute(statement):
            sql = str(statement)
            if 'ADD COLUMN' in sql:
                parts = sql.split()
                state['columns'][parts[2]].append(parts[8])
            elif 'DROP CONSTRAINT' in sql:
                state['checks'] = []
            elif 'ADD CONSTRAINT' in sql:
                state['checks'] = [{'name': PENALTY_CHECK, 'sqltext': PENALTY_EXPRESSION}]

        connection.execute.side_effect = execute
        with patch('migrate_learning_policy.inspect_schema', side_effect=lambda _: deepcopy(state)):
            self.assertEqual(apply_migration(connection), 4)
            self.assertEqual(apply_migration(connection), 0)
        self.assertEqual(connection.execute.call_count, 4)

    def test_check_inspects_only_and_apply_rejects_non_pg(self):
        connection = Mock(dialect=SimpleNamespace(name='sqlite'))
        with patch('migrate_learning_policy.inspect_schema', return_value=legacy_state()):
            self.assertFalse(schema_status(connection)['ready'])
            connection.execute.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'PostgreSQL'):
                apply_migration(connection)
            connection.execute.assert_not_called()

    def test_pg_model_columns_and_constraint_compile(self):
        for table, column in ((Challenge.__table__, 'learning_policy'),
                              (ChallengeLearningProgress.__table__, 'policy_snapshot')):
            self.assertTrue(table.c[column].nullable)
            self.assertIsNone(table.c[column].server_default)
            self.assertIn(f'{column} JSON', str(CreateTable(table).compile(dialect=postgresql.dialect())))
        ddl = str(CreateTable(ChallengeHintReveal.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn(f'CHECK ({PENALTY_EXPRESSION})', ddl)

    def test_additive_json_ddl_keeps_legacy_nulls_and_reveals(self):
        engine = create_engine('sqlite+pysqlite:///:memory:')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE challenges (id INTEGER PRIMARY KEY)'))
            connection.execute(text('CREATE TABLE challenge_learning_progress (id INTEGER PRIMARY KEY)'))
            connection.execute(text('CREATE TABLE challenge_hint_reveals '
                '(id INTEGER PRIMARY KEY, penalty_percent INTEGER, CONSTRAINT '
                'ck_learning_hint_penalty CHECK (penalty_percent = 10))'))
            connection.execute(text('INSERT INTO challenges VALUES (1)'))
            connection.execute(text('INSERT INTO challenge_learning_progress VALUES (2)'))
            connection.execute(text('INSERT INTO challenge_hint_reveals VALUES (3, 10)'))
            plan = migration_statements(inspect_schema(connection))
            # SQLite no admite IF NOT EXISTS en ADD COLUMN; las columnas se inspeccionaron ausentes.
            for statement in plan[:2]:
                connection.execute(text(statement.replace(' IF NOT EXISTS', '')))
            self.assertEqual(connection.execute(text('SELECT id, learning_policy FROM challenges')).all(), [(1, None)])
            self.assertEqual(connection.execute(text('SELECT id, policy_snapshot FROM challenge_learning_progress')).all(), [(2, None)])
            self.assertEqual(connection.execute(text('SELECT * FROM challenge_hint_reveals')).all(), [(3, 10)])
            self.assertEqual(len(migration_statements(inspect_schema(connection))), 2)


class LearningPolicyModelDataTests(unittest.TestCase):
    def test_penalties_accept_boundaries_and_keep_legacy_points_and_penalty(self):
        engine = create_engine('sqlite+pysqlite:///:memory:')
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(User(id=1, username='legacy', password_hash='test', role='player'))
            session.add(Challenge(id=1, code='LEGACY', name='Legacy', description='',
                instructions='', difficulty='Medio', category='MISC', mitre_technique='T1000',
                asset_references=[], points=200))
            session.flush()
            session.add(ChallengeLearningProgress(id=1, user_id=1, challenge_id=1,
                base_points=200, deadline=datetime.now(timezone.utc)))
            session.add(ChallengeCompletion(id=1, user_id=1, challenge_id=1, awarded_points=170))
            session.flush()
            session.add(ChallengeHintReveal(id=1, progress_id=1, hint_id=1, penalty_percent=10))
            session.commit()
            for hint_id, penalty in ((2, 0), (3, 100)):
                session.add(ChallengeHintReveal(progress_id=1, hint_id=hint_id, penalty_percent=penalty))
            session.commit()
            self.assertEqual(session.get(ChallengeHintReveal, 1).penalty_percent, 10)
            self.assertEqual(session.get(ChallengeCompletion, 1).awarded_points, 170)
            self.assertIsNone(session.get(Challenge, 1).learning_policy)
            self.assertIsNone(session.get(ChallengeLearningProgress, 1).policy_snapshot)
            for invalid in (-1, 101):
                with self.assertRaises(IntegrityError):
                    session.execute(text('UPDATE challenge_hint_reveals SET penalty_percent = :value WHERE id = 1'),
                                    {'value': invalid})
                    session.commit()
                session.rollback()
            self.assertEqual(session.get(ChallengeHintReveal, 1).penalty_percent, 10)
            self.assertEqual(session.get(ChallengeCompletion, 1).awarded_points, 170)


if __name__ == '__main__':
    unittest.main()
