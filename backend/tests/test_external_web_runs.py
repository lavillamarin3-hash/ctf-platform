"""Ciclo Cóndor real sobre SQLite efímera; cualquier acceso a VM falla.

Se ejecutan los endpoints y los ledgers reales. El adaptador solo convierte
SQLAlchemy síncrono en la interfaz asíncrona de la API y recupera UTC que SQLite
omite. No usa PostgreSQL, Docker, Guacamole, SSH ni peticiones al portal.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.api import runs
from app.core import hash_password, now_utc
from app.models import (
    AuditEvent, Base, Challenge, ChallengeCompletion, ChallengeFlag,
    ChallengeGroupAssignment, ChallengeHintReveal, ChallengeInstance,
    ChallengeLearningProgress, ChallengeRun, ChallengeRunFlag, GroupMembership,
    RemoteAccessAssignment, StudentGroup, Submission, User,
)
from app.schemas import SubmissionRequest
from app.services import external_web, learning
from app.services.condor_catalog import POLICY
from app.services.runtime_flags import EXPLICIT_STATIC_VALIDATOR


FLAG = 'COCIBER{ephemeral_external_web_runtime_test}'


class LocalSession:
    def __init__(self, engine):
        self.session = Session(engine, expire_on_commit=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.session.close()

    @staticmethod
    def aware(value):
        for name in ('started_at', 'expires_at', 'deadline', 'closed_at', 'solution_revealed_at'):
            date = getattr(value, name, None)
            if isinstance(date, datetime) and date.tzinfo is None:
                setattr(value, name, learning.utc(date))
        return value

    async def scalar(self, statement):
        return self.aware(self.session.scalar(statement))

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def get(self, model, identifier):
        return self.aware(self.session.get(model, identifier))

    def add(self, value):
        self.session.add(value)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()


class ExternalWebRunTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        event.listen(self.engine, 'connect', lambda db, _: db.execute('PRAGMA foreign_keys=ON'))
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = lambda: LocalSession(self.engine)
        self.now = now_utc()
        self.owner = SimpleNamespace(id=1, username='condor-owner', role='player')
        self.other = SimpleNamespace(id=2, username='condor-other', role='player')
        self.outsider = SimpleNamespace(id=3, username='condor-no-group', role='player')
        with Session(self.engine) as session:
            session.add_all([User(id=user.id, username=user.username, role=user.role,
                                 password_hash='!disabled!', is_active=True)
                             for user in (self.owner, self.other, self.outsider)])
            session.add(StudentGroup(id=1, code='45HY', name='verde', is_active=True))
            session.flush()
            challenge = Challenge(id=1, code=external_web.CODE, name='Operación Cóndor',
                description='Simulación local con datos ficticios.', instructions='Abre el portal local.',
                difficulty='Medio', category='WEB', scenario=external_web.SCENARIO,
                mitre_technique='T1110.001', points=250, is_published=True,
                asset_references=['CONDOR-PORTAL:http://localhost:8094/'],
                learning_policy=deepcopy(POLICY))
            challenge.flags = [ChallengeFlag(id=1, label='Evidencia', mode='static',
                validator=EXPLICIT_STATIC_VALIDATOR, flag_hash=hash_password(FLAG),
                flag_order=1, is_active=True)]
            session.add(challenge)
            session.flush()
            session.add_all([GroupMembership(group_id=1, user_id=1),
                             GroupMembership(group_id=1, user_id=2),
                             ChallengeGroupAssignment(challenge_id=1, group_id=1)])
            session.commit()

        self.forbidden = AsyncMock(side_effect=AssertionError('Cóndor local no debe acceder a VMs o Guacamole'))
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            session_factory=self.factory,
            redis=SimpleNamespace(incr=AsyncMock(return_value=1), expire=AsyncMock(),
                                  publish=AsyncMock(), set=self.forbidden, eval=self.forbidden),
            guacamole=SimpleNamespace(provision=self.forbidden, revoke=self.forbidden),
            guacamole_admin=SimpleNamespace(list_connections=self.forbidden,
                get_user_permissions=self.forbidden, patch_user_permissions=self.forbidden),
            flag_injector=SimpleNamespace(inject=self.forbidden, clear=self.forbidden, preflight=self.forbidden),
            terminal_sessions=SimpleNamespace(close_run=self.forbidden),
            sockets=SimpleNamespace(broadcast=AsyncMock()),
        )))
        patches = [patch.object(runs, 'now_utc', side_effect=lambda: self.now),
                   patch.object(learning, 'now_utc', side_effect=lambda: self.now),
                   patch.object(runs, '_find_challenge_vm', self.forbidden),
                   patch.object(runs, '_resolve_guacamole_connection', self.forbidden),
                   patch.object(runs, '_connection_protocol', self.forbidden),
                   patch.object(runs.kali_workspace, 'context', self.forbidden)]
        for service in (runs.ssh_practice, runs.http_practice, runs.vm_logic):
            patches.extend([patch.object(service, 'prepare', self.forbidden),
                            patch.object(service, 'cleanup', self.forbidden)])
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def tearDown(self):
        self.forbidden.assert_not_awaited()

    @staticmethod
    def data(response):
        return json.loads(response.body)

    def count(self, model, condition=None):
        with Session(self.engine) as session:
            statement = select(func.count()).select_from(model)
            return session.scalar(statement.where(condition) if condition is not None else statement)

    def update(self, model, identifier, **values):
        with Session(self.engine) as session:
            row = session.get(model, identifier)
            for key, value in values.items():
                setattr(row, key, value)
            session.commit()

    async def start(self):
        return await runs.start_challenge(external_web.CODE, self.request, self.owner)

    async def assert_http_error(self, status, call):
        with self.assertRaises(HTTPException) as raised:
            await call()
        self.assertEqual(raised.exception.status_code, status)

    async def test_start_creates_45_minute_ledger_without_vm_assignment_or_dynamic_flag(self):
        result = await self.start()
        self.assertEqual(result.workspace_strategy, external_web.STRATEGY)
        self.assertEqual(result.expires_at, self.now + timedelta(minutes=45))
        self.assertIsNone(result.launch_url)
        self.assertIsNone(result.target_vm_name)
        self.assertIsNone(result.target_vm_ip)
        self.assertIsNone(result.target_protocol)
        self.assertEqual(self.count(ChallengeRun), 1)
        self.assertEqual(self.count(ChallengeLearningProgress), 1)
        for model in (RemoteAccessAssignment, ChallengeInstance, ChallengeRunFlag):
            self.assertEqual(self.count(model), 0)
        with Session(self.engine) as session:
            progress = session.scalar(select(ChallengeLearningProgress))
            self.assertEqual(learning.utc(progress.deadline), result.expires_at)
            self.assertEqual(progress.policy_snapshot, POLICY)
            self.assertEqual(progress.first_run_id, result.id)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge_run.start'), 1)

    async def test_active_run_is_reused_without_duplicate_ledger_or_deadline_extension(self):
        first = await self.start()
        self.now += timedelta(minutes=5)
        again = await self.start()
        self.assertEqual(again.id, first.id)
        self.assertEqual(again.expires_at, first.expires_at)
        self.assertEqual(self.count(ChallengeRun), 1)
        self.assertEqual(self.count(ChallengeLearningProgress), 1)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge_run.start'), 1)

    async def test_start_requires_published_challenge_and_active_group_assignment(self):
        await self.assert_http_error(403, lambda: runs.start_challenge(
            external_web.CODE, self.request, self.outsider))
        self.update(StudentGroup, 1, is_active=False)
        await self.assert_http_error(403, self.start)
        self.update(StudentGroup, 1, is_active=True)
        self.update(Challenge, 1, is_published=False)
        await self.assert_http_error(404, self.start)
        self.assertEqual(self.count(ChallengeRun), 0)

    async def test_external_web_info_is_private_to_owner_and_has_no_secrets(self):
        run = await self.start()
        response = await runs.external_web_info(run.id, self.request, self.owner)
        data = self.data(response)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(data['portal_url'], 'http://localhost:8094/')
        self.assertEqual(data['mode'], 'local')
        self.assertEqual(set(data), {'title', 'portal_url', 'mode', 'objective', 'note'})
        self.assertNotIn(FLAG, json.dumps(data))
        await self.assert_http_error(404, lambda: runs.external_web_info(run.id, self.request, self.other))
        await self.assert_http_error(404, lambda: runs.external_web_info(999, self.request, self.owner))

    async def test_external_web_info_rejects_closed_expired_or_wrong_strategy(self):
        run = await self.start()
        for values in ({'status': 'closed'}, {'expires_at': self.now},
                       {'workspace_strategy': 'shared_lab_vm'}):
            with self.subTest(values=list(values)):
                self.update(ChallengeRun, run.id, status='active', expires_at=run.expires_at,
                            workspace_strategy=external_web.STRATEGY)
                self.update(ChallengeRun, run.id, **values)
                await self.assert_http_error(410, lambda: runs.external_web_info(run.id, self.request, self.owner))

    async def test_external_web_info_rechecks_publication_scenario_and_group_membership(self):
        run = await self.start()
        self.update(Challenge, 1, is_published=False)
        await self.assert_http_error(404, lambda: runs.external_web_info(run.id, self.request, self.owner))
        self.update(Challenge, 1, is_published=True, scenario='OTHER')
        await self.assert_http_error(404, lambda: runs.external_web_info(run.id, self.request, self.owner))
        self.update(Challenge, 1, scenario=external_web.SCENARIO)
        self.update(StudentGroup, 1, is_active=False)
        await self.assert_http_error(404, lambda: runs.external_web_info(run.id, self.request, self.owner))

    async def test_close_is_owner_only_and_idempotent_without_touching_portal_or_vm(self):
        run = await self.start()
        await self.assert_http_error(404, lambda: runs.close_run(run.id, self.request, self.other))
        closed = await runs.close_run(run.id, self.request, self.owner)
        self.assertEqual(closed.status, 'closed')
        self.assertEqual(closed.workspace_strategy, external_web.STRATEGY)
        self.assertIsNone(closed.target_vm_ip)
        with Session(self.engine) as session:
            saved = session.get(ChallengeRun, run.id)
            self.assertIsNotNone(saved.closed_at)
            self.assertEqual(learning.utc(saved.expires_at), run.expires_at)
        again = await runs.close_run(run.id, self.request, self.owner)
        self.assertEqual(again.status, 'closed')
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge_run.close'), 1)

    async def test_close_reopen_keeps_original_deadline_hint_costs_and_policy_snapshot(self):
        first = await self.start()
        hint = self.data(await runs.learning_hint(first.id, 1, self.request, self.owner))
        self.assertEqual(hint['available_points'], 225)
        await runs.close_run(first.id, self.request, self.owner)
        changed_policy = deepcopy(POLICY)
        changed_policy['duration_minutes'] = 120
        changed_policy['hints'][0]['penalty_percent'] = 40
        self.update(Challenge, 1, learning_policy=changed_policy, points=999)
        self.now += timedelta(minutes=5)
        reopened = await self.start()
        self.assertNotEqual(reopened.id, first.id)
        self.assertEqual(reopened.expires_at, first.expires_at)
        metadata = self.data(await runs.learning_info(reopened.id, self.request, self.owner))
        self.assertEqual(metadata['base_points'], 250)
        self.assertEqual(metadata['available_points'], 225)
        self.assertEqual(metadata['hints_used'], 1)
        self.assertEqual(metadata['hints'][0]['penalty_percent'], 10)
        self.assertEqual(self.count(ChallengeLearningProgress), 1)
        self.assertEqual(self.count(ChallengeHintReveal), 1)

    async def test_solution_requires_expiry_and_returns_walkthrough_without_flag_or_hash(self):
        run = await self.start()
        await self.assert_http_error(409, lambda: runs.learning_solution(run.id, self.request, self.owner))
        self.now = run.expires_at + timedelta(seconds=1)
        response = await runs.learning_solution(run.id, self.request, self.owner)
        data = self.data(response)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertTrue(data['expired'])
        self.assertEqual(data['available_points'], 62)
        self.assertTrue(data['solution_revealed'])
        self.assertIsNone(data['solution']['answer'])
        self.assertTrue(data['solution']['steps'])
        serialized = json.dumps(data)
        self.assertNotIn(FLAG, serialized)
        self.assertNotIn('$argon2', serialized)
        self.assertNotIn('Servicio2026', serialized)
        self.assertEqual(self.count(Submission), 0)
        self.assertEqual(self.count(ChallengeCompletion), 0)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge.solution.reveal'), 1)

    async def test_real_static_flag_submission_uses_hint_discount_and_awards_once(self):
        run = await self.start()
        await runs.learning_hint(run.id, 1, self.request, self.owner)
        wrong = await runs.submit_flag(external_web.CODE, SubmissionRequest(value='wrong-answer'),
                                       self.request, self.owner)
        self.assertFalse(wrong.correct)
        self.assertEqual(wrong.awarded_points, 0)
        result = await runs.submit_flag(external_web.CODE, SubmissionRequest(value=FLAG),
                                        self.request, self.owner)
        self.assertTrue(result.challenge_completed)
        self.assertEqual(result.awarded_points, 225)
        again = await runs.submit_flag(external_web.CODE, SubmissionRequest(value=FLAG),
                                       self.request, self.owner)
        self.assertTrue(again.correct)
        self.assertEqual(again.awarded_points, 0)
        self.assertEqual(self.count(ChallengeCompletion), 1)
        self.assertEqual(self.count(ChallengeRunFlag), 0)
        self.request.app.state.sockets.broadcast.assert_awaited_once()
