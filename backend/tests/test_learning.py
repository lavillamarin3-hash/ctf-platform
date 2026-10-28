"""Política de ayudas con SQLite real; sin SSH, Guacamole o bases externas."""
import asyncio
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import runs
from app.core import hash_password, now_utc, verify_password
from app.models import (AuditEvent, Base, Challenge, ChallengeCompletion, ChallengeFlag, ChallengeHintReveal,
                        ChallengeLearningProgress, ChallengeRun, ChallengeRunFlag, Submission, User)
from app.schemas import ChallengeCreate, LearningPolicy, SubmissionRequest
from app.services.bootstrap import challenge_view
from app.services import dynamic_flags, learning, offline_runtime
from migrate_learning import TABLES, create_tables


class AsyncSessionAdapter:
    """Adapta SQLite; emula únicamente los locks FOR UPDATE que SQLite ignora."""
    def __init__(self, engine, locks, statements):
        self.session = Session(engine, expire_on_commit=False)
        self.locks = locks
        self.statements = statements
        self.held = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.session.close()
        self.release_locks()

    def release_locks(self):
        for lock in self.held:
            lock.release()
        self.held.clear()

    @staticmethod
    def aware(value):
        # SQLite omite timezone=True; PostgreSQL entrega estos campos con UTC.
        for name in ('started_at', 'expires_at', 'deadline', 'closed_at', 'solution_revealed_at'):
            date = getattr(value, name, None)
            if isinstance(date, datetime) and date.tzinfo is None:
                setattr(value, name, learning.utc(date))
        return value

    async def scalar(self, statement):
        self.statements.append(statement)
        if statement.column_descriptions[0].get('entity') is User and statement._for_update_arg is not None:
            lock = self.locks.setdefault('user', asyncio.Lock())
            if lock not in self.held:
                await lock.acquire()
                self.held.append(lock)
                # Una pausa permite solapar peticiones antes del ledger.
                await asyncio.sleep(0)
        return self.aware(self.session.scalar(statement))

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def get(self, model, identifier):
        return self.aware(self.session.get(model, identifier))

    async def refresh(self, value, attribute_names=None):
        self.session.refresh(value, attribute_names=attribute_names)

    def add(self, value):
        self.session.add(value)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()
        self.release_locks()

    async def rollback(self):
        self.session.rollback()
        self.release_locks()


class LearningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.locks, self.statements = {}, []
        self.factory = lambda: AsyncSessionAdapter(self.engine, self.locks, self.statements)
        self.now = now_utc()
        self.user = SimpleNamespace(id=1, username='learner', role='player')
        self.other = SimpleNamespace(id=2, username='other', role='player')
        with Session(self.engine) as session:
            session.add_all([User(id=1, username='learner', password_hash='test', role='player'),
                             User(id=2, username='other', password_hash='test', role='player')])
            challenge = Challenge(id=1, code='CRY-01', name='Base64', description='Mensaje de práctica',
                instructions='', difficulty='Básico', category='CRYPTO', mitre_technique='T1000',
                asset_references=['OFFLINE-CASE', 'LAB-KALI'], points=250, is_published=True)
            challenge.flags = [ChallengeFlag(id=1, label='Respuesta', mode='dynamic', flag_order=1,
                                             template='FLAG{offline_{{RAND}}}', is_active=True)]
            session.add(challenge)
            run = ChallengeRun(id=10, user_id=1, challenge_id=1, status='active', started_at=self.now,
                               expires_at=self.now + timedelta(hours=1), workspace_strategy='offline_case')
            session.add(run)
            session.flush()
            session.add(ChallengeRunFlag(run_id=10, flag_id=1,
                flag_hash=hash_password(offline_runtime.flag_for(run)), fingerprint='x'*64))
            session.add(ChallengeLearningProgress(id=1, user_id=1, challenge_id=1, first_run_id=10,
                base_points=250, deadline=run.expires_at, policy_version=1, is_assisted=False))
            session.commit()
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            session_factory=self.factory, redis=SimpleNamespace(publish=AsyncMock()),
            sockets=SimpleNamespace(broadcast=AsyncMock()))))
        self.patches = [patch.object(runs, '_assigned', AsyncMock(return_value=True)),
                        patch.object(runs, 'check_rate_limit', AsyncMock()),
                        patch.object(runs, 'write_audit', AsyncMock()),
                        patch.object(runs, 'ranking_rows', AsyncMock(return_value=[])),
                        patch.object(learning, 'now_utc', return_value=self.now),
                        patch.object(runs, 'now_utc', return_value=self.now)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    @staticmethod
    def data(response):
        return json.loads(response.body)

    def expire(self):
        with Session(self.engine) as session:
            progress = session.get(ChallengeLearningProgress, 1)
            progress.deadline = self.now
            session.get(ChallengeRun, 10).status = 'expired'
            session.get(ChallengeRun, 10).expires_at = self.now
            session.commit()

    async def test_metadata_has_no_hidden_content_or_answer_and_three_costs(self):
        result = self.data(await runs.learning_info(10, self.request, self.user))
        self.assertEqual(result['base_points'], 250)
        self.assertEqual(result['available_points'], 250)
        self.assertEqual(result['hints_used'], 0)
        self.assertNotIn('solution', result)
        self.assertTrue(all(set(hint) == {'id', 'title', 'unlocked', 'penalty_percent'} for hint in result['hints']))
        for hint, points in ((1, 225), (2, 200), (3, 175)):
            response = await runs.learning_hint(10, hint, self.request, self.user)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            result = self.data(response)
            self.assertEqual(result['hints_used'], hint)
            self.assertEqual(result['available_points'], points)
            self.assertEqual(sum('content' in row for row in result['hints']), hint)
        again = self.data(await runs.learning_hint(10, 3, self.request, self.user))
        self.assertEqual(again['available_points'], 175)
        with Session(self.engine) as session:
            self.assertEqual(len(session.scalars(select(ChallengeHintReveal)).all()), 3)

    async def test_order_closed_and_invalid_hint_are_rejected_without_charge(self):
        for hint, expected in ((0, 404), (4, 404), (3, 409), (2, 409)):
            with self.assertRaises(HTTPException) as raised:
                await runs.learning_hint(10, hint, self.request, self.user)
            self.assertEqual(raised.exception.status_code, expected)
        with Session(self.engine) as session:
            session.get(ChallengeRun, 10).status = 'closed'
            session.commit()
        with self.assertRaises(HTTPException):
            await runs.learning_hint(10, 1, self.request, self.user)
        result = self.data(await runs.learning_info(10, self.request, self.user))
        self.assertEqual(result['hints_used'], 0)

    async def test_solution_cannot_be_built_or_leaked_before_deadline(self):
        with patch.object(learning, 'solution_for') as build:
            with self.assertRaises(HTTPException) as raised:
                await runs.learning_solution(10, self.request, self.user)
            self.assertEqual(raised.exception.status_code, 409)
            build.assert_not_called()
        self.expire()
        result = self.data(await runs.learning_solution(10, self.request, self.user))
        self.assertEqual(result['available_points'], 62)
        self.assertTrue(result['expired'])
        self.assertIsInstance(result['solution']['answer'], str)
        self.assertGreater(len(result['solution']['steps']), 0)
        with Session(self.engine) as session:
            run = session.get(ChallengeRun, 10)
            _, expected = offline_runtime.case_for(run, 'CRY-01')
            self.assertEqual(result['solution']['answer'], expected)
            self.assertIsNotNone(session.get(ChallengeLearningProgress, 1).solution_revealed_at)
        with self.assertRaises(HTTPException):
            await runs.learning_hint(10, 1, self.request, self.user)

    async def test_owner_published_and_assignment_on_every_endpoint(self):
        endpoints = (lambda user: runs.learning_info(10, self.request, user),
                     lambda user: runs.learning_hint(10, 1, self.request, user),
                     lambda user: runs.learning_solution(10, self.request, user),
                     lambda user: runs.learning_complete(10, self.request, user))
        for endpoint in endpoints:
            with self.assertRaises(HTTPException) as raised:
                await endpoint(self.other)
            self.assertEqual(raised.exception.status_code, 404)
        for available in (False, True):
            with Session(self.engine) as session:
                session.get(Challenge, 1).is_published = available
                session.commit()
            with patch.object(runs, '_assigned', AsyncMock(return_value=False)):
                for endpoint in endpoints:
                    with self.assertRaises(HTTPException) as raised:
                        await endpoint(self.user)
                    self.assertEqual(raised.exception.status_code, 404)

    async def test_reopening_keeps_snapshot_deadline_and_hints_without_historical_backfill(self):
        await runs.learning_hint(10, 1, self.request, self.user)
        with Session(self.engine) as session:
            original_deadline = session.get(ChallengeLearningProgress, 1).deadline
            session.get(Challenge, 1).points = 999
            session.get(ChallengeRun, 10).status = 'closed'
            session.add(ChallengeRun(id=11, user_id=1, challenge_id=1, status='active', started_at=self.now,
                                    expires_at=self.now + timedelta(hours=4), workspace_strategy='offline_case'))
            session.add(ChallengeRun(id=9, user_id=1, challenge_id=1, status='closed', started_at=self.now - timedelta(days=5),
                                    expires_at=self.now - timedelta(days=4), workspace_strategy='offline_case'))
            session.commit()
        async with self.factory() as session:
            state = await learning.lock_progress(session, await session.get(ChallengeRun, 11),
                                                  await session.get(Challenge, 1), create=True)
            self.assertEqual(learning.utc(state.deadline), learning.utc(original_deadline))
            self.assertEqual(state.base_points, 250)
            await session.commit()
        result = self.data(await runs.learning_info(11, self.request, self.user))
        self.assertEqual(result['available_points'], 225)
        self.assertTrue(result['hints'][0]['unlocked'])
        with self.assertRaises(HTTPException) as legacy:
            await runs.learning_info(9, self.request, self.user)
        self.assertEqual(legacy.exception.status_code, 409)
        with Session(self.engine) as session:
            session.delete(session.get(ChallengeLearningProgress, 1))
            session.commit()
        with self.assertRaises(HTTPException):
            await runs.learning_info(11, self.request, self.user)

    async def test_normal_submission_uses_server_discount_and_preserves_historical_completion(self):
        await runs.learning_hint(10, 1, self.request, self.user)
        with Session(self.engine) as session:
            value = offline_runtime.flag_for(session.get(ChallengeRun, 10))
        result = await runs.submit_flag('CRY-01', SubmissionRequest(value=value), self.request, self.user)
        self.assertEqual(result.awarded_points, 225)
        self.assertTrue(result.challenge_completed)
        self.expire()
        await runs.learning_solution(10, self.request, self.user)
        again = self.data(await runs.learning_complete(10, self.request, self.user))
        self.assertEqual(again['awarded_points'], 0)
        with Session(self.engine) as session:
            completions = session.scalars(select(ChallengeCompletion)).all()
            self.assertEqual(len(completions), 1)
            self.assertEqual(completions[0].awarded_points, 225)
        metadata = self.data(await runs.learning_info(10, self.request, self.user))
        self.assertEqual(metadata['awarded_points'], 225)
        self.assertEqual(metadata['available_points'], 225)

    async def test_assisted_expiration_is_exact_quarter_once_and_never_fakes_submission(self):
        for hint in (1, 2, 3):
            await runs.learning_hint(10, hint, self.request, self.user)
        self.expire()
        with self.assertRaises(HTTPException):
            await runs.learning_complete(10, self.request, self.user)
        await runs.learning_solution(10, self.request, self.user)
        responses = await asyncio.gather(runs.learning_complete(10, self.request, self.user),
                                         runs.learning_complete(10, self.request, self.user))
        self.assertEqual(sorted(self.data(response)['awarded_points'] for response in responses), [0, 62])
        with Session(self.engine) as session:
            self.assertEqual(len(session.scalars(select(ChallengeCompletion)).all()), 1)
            self.assertEqual(session.scalars(select(Submission)).all(), [])
            self.assertTrue(session.get(ChallengeLearningProgress, 1).is_assisted)
        self.request.app.state.sockets.broadcast.assert_awaited_once()

    async def test_concurrent_reveal_and_submission_share_user_lock_and_unique_ledger(self):
        with Session(self.engine) as session:
            value = offline_runtime.flag_for(session.get(ChallengeRun, 10))
        await asyncio.gather(runs.learning_hint(10, 1, self.request, self.user),
                             runs.learning_hint(10, 1, self.request, self.user),
                             runs.submit_flag('CRY-01', SubmissionRequest(value=value), self.request, self.user))
        with Session(self.engine) as session:
            self.assertEqual(len(session.scalars(select(ChallengeHintReveal)).all()), 1)
            completion = session.scalar(select(ChallengeCompletion))
            self.assertEqual(completion.awarded_points, 225)
        lock_sql = [str(statement.compile(dialect=postgresql.dialect())) for statement in self.statements
                    if statement.column_descriptions[0].get('entity') in (User, ChallengeLearningProgress)]
        self.assertTrue(lock_sql)
        self.assertTrue(all('FOR UPDATE' in sql for sql in lock_sql))

    async def test_zero_point_assisted_completion_still_broadcasts_and_reports_completion(self):
        with Session(self.engine) as session:
            session.get(ChallengeLearningProgress, 1).base_points = 3
            session.commit()
        self.expire()
        await runs.learning_solution(10, self.request, self.user)
        result = self.data(await runs.learning_complete(10, self.request, self.user))
        self.assertEqual(result['awarded_points'], 0)
        self.assertTrue(result['challenge_completed'])
        self.assertIn('registrado', result['message'])
        self.request.app.state.sockets.broadcast.assert_awaited_once()

    async def test_first_new_attempt_creates_ledger_from_current_run_only(self):
        with Session(self.engine) as session:
            session.delete(session.get(ChallengeLearningProgress, 1))
            session.add(ChallengeRun(id=20, user_id=1, challenge_id=1, status='active', started_at=self.now,
                                    expires_at=self.now + timedelta(hours=2), workspace_strategy='offline_case'))
            session.commit()
        async with self.factory() as session:
            run = await session.get(ChallengeRun, 20)
            progress = await learning.lock_progress(session, run, await session.get(Challenge, 1), create=True)
            self.assertEqual(progress.first_run_id, 20)
            self.assertEqual(learning.utc(progress.deadline), learning.utc(run.expires_at))
            await session.commit()

    async def prepare_shared(self, code):
        with Session(self.engine) as session:
            challenge = session.get(Challenge, 1)
            challenge.code = code
            flag = session.get(ChallengeFlag, 1)
            flag.template = 'FLAG{{{CODE}}_{{USER}}_{{RUN_ID}}_{{RAND}}}'
            session.get(ChallengeRun, 10).workspace_strategy = 'shared_lab_vm'
            for flag_hash in session.scalars(select(ChallengeRunFlag)).all():
                session.delete(flag_hash)
            session.commit()
        injector = SimpleNamespace(inject=AsyncMock(), clear=AsyncMock())
        settings = SimpleNamespace(flag_injector_enabled=True, flag_injector_flag_path='/opt/ctf/flag.txt')
        async with self.factory() as session:
            with patch.object(dynamic_flags, 'get_settings', return_value=settings):
                await dynamic_flags.DynamicFlagRuntime(injector).prepare(
                    session, await session.get(Challenge, 1), await session.get(ChallengeRun, 10),
                    self.user.username, SimpleNamespace(ip_address='192.0.2.1', os='Linux'))
            await session.commit()
        return injector.inject.await_args.args[2]

    async def check_shared_solution(self, code):
        private_settings = SimpleNamespace(field_hmac_secret='test-private-shared-flag-key')
        with patch('app.core.get_settings', return_value=private_settings):
            value = await self.prepare_shared(code)
            with Session(self.engine) as session:
                stored_hash = session.scalar(select(ChallengeRunFlag)).flag_hash
                self.assertTrue(verify_password(value, stored_hash))
                marker = session.scalar(select(AuditEvent).where(AuditEvent.action == dynamic_flags.DERIVATION_ACTION))
                serialized = json.dumps(marker.details)
                self.assertNotIn(value, serialized)
                self.assertNotIn(private_settings.field_hmac_secret, serialized)
            metadata = self.data(await runs.learning_info(10, self.request, self.user))
            self.assertNotIn(value, json.dumps(metadata))
            with patch.object(learning, 'solution_for_run', AsyncMock()) as provider:
                with self.assertRaises(HTTPException) as before:
                    await runs.learning_solution(10, self.request, self.user)
                self.assertEqual(before.exception.status_code, 409)
                provider.assert_not_awaited()
            # La reconstrucción usa la plantilla/nombre originales del evento,
            # no la configuración editable cuando se consulta la solución.
            with Session(self.engine) as session:
                session.get(ChallengeFlag, 1).template = 'FLAG{config_changed_{{RAND}}}'
                session.get(User, 1).username = 'renamed-learner'
                session.commit()
            self.expire()
            response = await runs.learning_solution(10, self.request, self.user)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            result = self.data(response)
            self.assertEqual(result['solution']['answer'], value)
            self.assertEqual(result['available_points'], 62)
            with Session(self.engine) as session:
                self.assertEqual(session.scalar(select(ChallengeRunFlag)).flag_hash, stored_hash)

    async def test_new_lab01_solution_matches_its_injected_and_persisted_flag(self):
        await self.check_shared_solution('LAB-01')

    async def test_new_esc01_solution_matches_its_injected_and_persisted_flag(self):
        await self.check_shared_solution('ESC-01-RECON')

    async def test_shared_legacy_without_marker_keeps_hash_and_does_not_invent_answer(self):
        legacy = 'FLAG{previous_random_value}'
        with Session(self.engine) as session:
            session.get(Challenge, 1).code = 'LAB-01'
            session.get(ChallengeRun, 10).workspace_strategy = 'shared_lab_vm'
            session.scalar(select(ChallengeRunFlag)).flag_hash = hash_password(legacy)
            session.commit()
        self.expire()
        response = self.data(await runs.learning_solution(10, self.request, self.user))
        self.assertIsNone(response['solution']['answer'])
        with Session(self.engine) as session:
            self.assertTrue(verify_password(legacy, session.scalar(select(ChallengeRunFlag)).flag_hash))
            self.assertEqual(session.scalars(select(AuditEvent)).all(), [])

    async def test_rotated_key_or_invalid_snapshot_never_returns_unverified_flag(self):
        with patch('app.core.get_settings', return_value=SimpleNamespace(field_hmac_secret='original-test-key')):
            value = await self.prepare_shared('LAB-01')
        self.expire()
        with patch('app.core.get_settings', return_value=SimpleNamespace(field_hmac_secret='rotated-test-key')):
            response = self.data(await runs.learning_solution(10, self.request, self.user))
            self.assertIsNone(response['solution']['answer'])
        with Session(self.engine) as session:
            marker = session.scalar(select(AuditEvent))
            invalid = dict(marker.details)
            invalid['flags'] = [{**invalid['flags'][0], 'template': 'FLAG{tampered_{{RAND}}}'}]
            marker.details = invalid
            session.commit()
        with patch('app.core.get_settings', return_value=SimpleNamespace(field_hmac_secret='original-test-key')):
            response = self.data(await runs.learning_solution(10, self.request, self.user))
            self.assertIsNone(response['solution']['answer'])
        with Session(self.engine) as session:
            self.assertTrue(verify_password(value, session.scalar(select(ChallengeRunFlag)).flag_hash))

    def configurable_policy(self):
        return {'duration_minutes': 37, 'expired_points_percent': 40,
                'hints': [{'title': 'Adquiere', 'content': 'Material privado de {{RUN_ID}}', 'penalty_percent': 20},
                          {'title': 'Relaciona', 'content': 'Segunda ayuda privada', 'penalty_percent': 5}],
                'solution_text': 'Explicación privada de {{RUN_ID}}\nComprueba el resultado.'}

    async def start_configured(self):
        with Session(self.engine) as session:
            session.get(Challenge, 1).learning_policy = self.configurable_policy()
            session.get(ChallengeRun, 10).status = 'closed'
            session.delete(session.get(ChallengeLearningProgress, 1))
            session.commit()
        return await runs.start_challenge('CRY-01', self.request, self.user)

    async def test_custom_policy_controls_real_duration_snapshot_cost_and_solution(self):
        run = await self.start_configured()
        self.assertEqual(learning.utc(run.expires_at), self.now + timedelta(minutes=37))
        initial = self.data(await runs.learning_info(run.id, self.request, self.user))
        self.assertEqual(initial['hint_count'], 2)
        self.assertEqual(initial['expired_points_percent'], 40)
        self.assertEqual([hint['penalty_percent'] for hint in initial['hints']], [20, 5])
        self.assertNotIn('Material privado', json.dumps(initial))
        self.assertNotIn('Explicación privada', json.dumps(initial))
        with self.assertRaises(HTTPException):
            await runs.learning_hint(run.id, 3, self.request, self.user)
        result = self.data(await runs.learning_hint(run.id, 1, self.request, self.user))
        self.assertEqual(result['available_points'], 200)
        self.assertEqual(result['hints'][0]['content'], f'Material privado de {run.id}')
        repeated = self.data(await runs.learning_hint(run.id, 1, self.request, self.user))
        self.assertEqual(repeated['available_points'], 200)
        result = self.data(await runs.learning_hint(run.id, 2, self.request, self.user))
        self.assertEqual(result['available_points'], 187)
        with Session(self.engine) as session:
            progress = session.scalar(select(ChallengeLearningProgress))
            progress.deadline = self.now
            reveals = session.scalars(select(ChallengeHintReveal).order_by(ChallengeHintReveal.hint_id)).all()
            self.assertEqual([reveal.penalty_percent for reveal in reveals], [20, 5])
            session.commit()
        revealed = self.data(await runs.learning_solution(run.id, self.request, self.user))
        self.assertEqual(revealed['available_points'], 100)
        self.assertEqual(revealed['solution']['steps'], [f'Explicación privada de {run.id}', 'Comprueba el resultado.'])
        self.assertIsInstance(revealed['solution']['answer'], str)
        completed = self.data(await runs.learning_complete(run.id, self.request, self.user))
        self.assertEqual(completed['awarded_points'], 100)
        self.assertIn('100 puntos', completed['message'])

    async def test_editing_policy_during_active_run_does_not_change_snapshot_or_reopen_deadline(self):
        from app.api.challenges import update_challenge
        run = await self.start_configured()
        await runs.learning_hint(run.id, 1, self.request, self.user)
        with Session(self.engine) as session:
            challenge = session.get(Challenge, 1)
            values = {key: getattr(challenge, key) for key in ChallengeCreate.model_fields if key != 'learning_policy'}
        replacement = {'duration_minutes': 1440, 'expired_points_percent': 99,
                       'hints': [{'title': 'Nueva', 'content': 'No retroactiva', 'penalty_percent': 0}],
                       'solution_text': 'Solución no retroactiva'}
        payload = ChallengeCreate(**values, learning_policy=replacement)
        with patch('app.api.challenges.write_audit', AsyncMock()), \
             patch('app.api.challenges.require_idle_challenge', AsyncMock(side_effect=AssertionError('No debe impedir editar solo la política'))):
            await update_challenge('CRY-01', payload, self.request, SimpleNamespace(id=1, role='instructor'))
        unchanged = self.data(await runs.learning_info(run.id, self.request, self.user))
        self.assertEqual(unchanged['hint_count'], 2)
        self.assertEqual(unchanged['expired_points_percent'], 40)
        self.assertEqual(unchanged['available_points'], 200)
        with Session(self.engine) as session:
            session.get(ChallengeRun, run.id).status = 'closed'
            session.commit()
        reopened = await runs.start_challenge('CRY-01', self.request, self.user)
        self.assertEqual(learning.utc(reopened.expires_at), learning.utc(run.expires_at))
        future = self.now + timedelta(minutes=40)
        with Session(self.engine) as session:
            session.get(ChallengeRun, reopened.id).status = 'closed'
            session.commit()
        with patch.object(runs, 'now_utc', return_value=future), patch.object(learning, 'now_utc', return_value=future):
            practice = await runs.start_challenge('CRY-01', self.request, self.user)
            self.assertEqual(learning.utc(practice.expires_at), future + timedelta(minutes=37))
            metadata = self.data(await runs.learning_info(practice.id, self.request, self.user))
            self.assertTrue(metadata['expired'])
            self.assertEqual(metadata['available_points'], 100)
            self.assertEqual(learning.utc(datetime.fromisoformat(metadata['deadline'])), learning.utc(run.expires_at))

    async def test_old_put_omitting_policy_preserves_config_and_legacy_ledger_keeps_ten_twentyfive(self):
        from app.api.challenges import update_challenge
        with Session(self.engine) as session:
            challenge = session.get(Challenge, 1)
            challenge.learning_policy = self.configurable_policy()
            values = {key: getattr(challenge, key) for key in ChallengeCreate.model_fields if key != 'learning_policy'}
            session.commit()
        with patch('app.api.challenges.write_audit', AsyncMock()):
            await update_challenge('CRY-01', ChallengeCreate(**values), self.request, SimpleNamespace(id=1))
        with Session(self.engine) as session:
            self.assertEqual(session.get(Challenge, 1).learning_policy, self.configurable_policy())
            self.assertIsNone(session.get(ChallengeLearningProgress, 1).policy_snapshot)
        legacy = self.data(await runs.learning_hint(10, 1, self.request, self.user))
        self.assertEqual(legacy['available_points'], 225)
        self.assertEqual(legacy['hint_count'], 3)
        self.assertEqual(legacy['expired_points_percent'], 25)
        self.expire()
        revealed = self.data(await runs.learning_solution(10, self.request, self.user))
        self.assertNotIn('Explicación privada', json.dumps(revealed))
        self.assertEqual(revealed['available_points'], 62)

    async def test_free_hint_and_zero_or_full_expired_percent_are_supported(self):
        for percentage in (0, 100):
            with self.subTest(percentage=percentage), Session(self.engine) as session:
                progress = session.get(ChallengeLearningProgress, 1)
                policy = self.configurable_policy()
                policy['expired_points_percent'] = percentage
                policy['hints'] = [{'title': 'Ayuda gratuita', 'content': 'Una pista', 'penalty_percent': 0}]
                progress.policy_snapshot = policy
                progress.deadline = self.now + timedelta(minutes=37)
                session.get(ChallengeRun, 10).status = 'active'
                session.get(ChallengeRun, 10).expires_at = progress.deadline
                for completion in session.scalars(select(ChallengeCompletion)).all():
                    session.delete(completion)
                for reveal in session.scalars(select(ChallengeHintReveal)).all():
                    session.delete(reveal)
                session.commit()
            hinted = self.data(await runs.learning_hint(10, 1, self.request, self.user))
            self.assertEqual(hinted['available_points'], 250)
            self.expire()
            await runs.learning_solution(10, self.request, self.user)
            awarded = self.data(await runs.learning_complete(10, self.request, self.user))
            self.assertEqual(awarded['awarded_points'], 250 * percentage // 100)

    async def test_admin_policy_view_is_editable_and_private_student_view_never_contains_closed_content(self):
        with Session(self.engine) as session:
            challenge = session.get(Challenge, 1)
            defaults = challenge_view(challenge, include_flags=True).learning_policy
            self.assertEqual(defaults.duration_minutes, 240)
            self.assertEqual(len(defaults.hints), 3)
            challenge.code = 'ESC-02-BRUTEFORCE'
            challenge.scenario = 'SSH-PASSWORD-LAB'
            challenge.asset_references = ['LAB-KALI', 'LAB-LNXVICT']
            ssh_defaults = challenge_view(challenge, include_flags=True).learning_policy.model_dump_json()
            self.assertIn('ctf{{RUN_ID}}', ssh_defaults)
            self.assertNotIn('ctf0', ssh_defaults)
            challenge.learning_policy = self.configurable_policy()
            admin = challenge_view(challenge, include_flags=True).model_dump_json()
            public = challenge_view(challenge, include_flags=False).model_dump_json()
            self.assertIn('Explicación privada', admin)
            self.assertIn('Material privado', admin)
            self.assertNotIn('Explicación privada', public)
            self.assertNotIn('Material privado', public)


class LearningSchemaTests(unittest.TestCase):
    def test_migration_only_creates_two_tables_idempotently_and_constraints_hold(self):
        engine = create_engine('sqlite+pysqlite:///:memory:')
        try:
            old_tables = [table for table in Base.metadata.sorted_tables if table not in TABLES]
            Base.metadata.create_all(engine, tables=old_tables)
            with Session(engine) as session:
                session.add(ChallengeCompletion(user_id=1, challenge_id=1, awarded_points=413))
                session.commit()
            before = set(inspect(engine).get_table_names())
            with engine.begin() as connection:
                create_tables(connection)
                create_tables(connection)
            self.assertEqual(set(inspect(engine).get_table_names()) - before, {table.name for table in TABLES})
            with Session(engine) as session:
                self.assertEqual(session.scalar(select(ChallengeCompletion)).awarded_points, 413)
                self.assertEqual(session.scalars(select(ChallengeLearningProgress)).all(), [])
                first = ChallengeLearningProgress(user_id=1, challenge_id=1, base_points=250, deadline=now_utc())
                session.add(first)
                session.commit()
                session.add(ChallengeLearningProgress(user_id=1, challenge_id=1, base_points=250, deadline=now_utc()))
                with self.assertRaises(IntegrityError):
                    session.commit()
                session.rollback()
                session.add_all([ChallengeHintReveal(progress_id=first.id, hint_id=1),
                                 ChallengeHintReveal(progress_id=first.id, hint_id=1)])
                with self.assertRaises(IntegrityError):
                    session.commit()
        finally:
            engine.dispose()


class LearningSolutionProviderTests(unittest.TestCase):
    def test_all_catalog_families_and_live_vm_providers_return_complete_serializable_solution(self):
        from app.domain.challenges.offline import CATALOG
        from app.services import http_practice, vm_logic
        cases = [(code, 'offline_case') for code in CATALOG]
        cases.extend([('DFIR-01', 'dfir_case'), ('ESC-02-BRUTEFORCE', 'ssh_password_lab'),
                      ('ESC-06-WEBAUTH', 'http_password_lab'), ('ESC-07-EXPOSED', 'http_files_lab'),
                      ('LAB-01', 'shared_lab_vm'), ('ESC-01-RECON', 'shared_lab_vm')])
        cases.extend((code, vm_logic.STRATEGY) for code in vm_logic.CODES)
        for code, strategy in cases:
            with self.subTest(code=code, strategy=strategy):
                run = SimpleNamespace(id=42, user_id=8, challenge_id=1, workspace_strategy=strategy)
                result = learning.solution_for(run, SimpleNamespace(code=code))
                self.assertIsInstance(result['steps'], list)
                self.assertGreaterEqual(len(result['steps']), 3)
                self.assertTrue(all(isinstance(step, str) and step.strip() for step in result['steps']))
                self.assertIsInstance(result['answer'], (str, type(None)))
                json.dumps(result)
                if strategy == 'vm_logic_lab':
                    self.assertEqual(json.loads(result['answer']), vm_logic.case_for(run, code)[1])
                elif strategy == 'http_files_lab':
                    self.assertEqual(json.loads(result['answer']), http_practice.case_for(run)[1])
                elif strategy == 'shared_lab_vm':
                    self.assertIsNone(result['answer'])


class LearningPolicyValidationTests(unittest.TestCase):
    def test_boundaries_and_total_penalty(self):
        from pydantic import ValidationError
        valid = {'duration_minutes': 1, 'expired_points_percent': 0,
                 'hints': [{'title': 'Pista', 'content': 'Texto útil', 'penalty_percent': 100}]}
        self.assertEqual(LearningPolicy(**valid).duration_minutes, 1)
        self.assertEqual(LearningPolicy(**{**valid, 'timer_enabled': False, 'hints': []}).hints, [])
        self.assertEqual(LearningPolicy(**{**valid, 'duration_minutes': 1440, 'expired_points_percent': 100}).expired_points_percent, 100)
        invalid = [{**valid, 'duration_minutes': 0}, {**valid, 'duration_minutes': 1441},
                   {**valid, 'expired_points_percent': -1}, {**valid, 'expired_points_percent': 101},
                   {**valid, 'hints': valid['hints'] * 4},
                   {**valid, 'hints': [valid['hints'][0], {'title': 'Otra', 'content': 'Texto', 'penalty_percent': 1}]},
                   {**valid, 'hints': [{'title': ' ', 'content': 'Texto', 'penalty_percent': 1}]},
                   {**valid, 'hints': [{'title': 'Pista', 'content': ' ', 'penalty_percent': 1}]},
                   {**valid, 'solution_text': 'a' * 12001}]
        for policy in invalid:
            with self.subTest(policy=policy), self.assertRaises(ValidationError):
                LearningPolicy(**policy)


if __name__ == '__main__':
    unittest.main()
