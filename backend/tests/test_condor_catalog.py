"""Configura exclusivamente una base SQLite efímera con FK activadas."""
from copy import deepcopy
import io
import json
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.core import verify_password
from app.models import AuditEvent, Base, Challenge, ChallengeFlag, ChallengeGroupAssignment, StudentGroup
from app.schemas import LearningPolicy
from app.services.condor_catalog import POLICY, configure
from app.services.external_web import CODE, SCENARIO
from app.services.runtime_flags import EXPLICIT_STATIC_VALIDATOR
from configure_condor_challenge import read_config


FLAG = 'COCIBER{only_ephemeral_catalog_test}'
URL = 'http://localhost:8094/'


class AsyncSessionAdapter:
    def __init__(self, session):
        self.session = session

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, value):
        self.session.add(value)

    async def flush(self):
        self.session.flush()


class CondorCatalogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        event.listen(self.engine, 'connect', lambda db, _: db.execute('PRAGMA foreign_keys=ON'))
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.session.close)
        self.session.add(StudentGroup(id=1, code='45HY', name='verde', is_active=True))
        self.session.commit()
        self.adapter = AsyncSessionAdapter(self.session)

    async def create(self):
        result = await configure(self.adapter, URL, FLAG)
        self.session.flush()
        challenge = self.session.scalar(select(Challenge).where(Challenge.code == CODE))
        return result, challenge

    async def test_creates_published_local_challenge_one_static_hash_and_group(self):
        report, challenge = await self.create()
        self.assertTrue(report['created'])
        self.assertEqual((challenge.name, challenge.points, challenge.difficulty),
            ('Operación Cóndor: acceso al centro de mando', 250, 'Medio'))
        self.assertEqual(challenge.scenario, SCENARIO)
        self.assertEqual(challenge.asset_references, ['CONDOR-PORTAL:' + URL])
        self.assertTrue(challenge.is_published)
        self.assertIn('no necesita una terminal SSH o RDP', challenge.instructions)
        self.assertEqual(len(challenge.flags), 1)
        flag = challenge.flags[0]
        self.assertEqual((flag.mode, flag.validator, flag.is_active),
            ('static', EXPLICIT_STATIC_VALIDATOR, True))
        self.assertIsNone(flag.template)
        self.assertTrue(verify_password(FLAG, flag.flag_hash))
        self.assertNotIn(FLAG, flag.flag_hash)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ChallengeGroupAssignment)), 1)
        LearningPolicy.model_validate(challenge.learning_policy)
        self.assertEqual(challenge.learning_policy, POLICY)
        serialized = json.dumps({'report': report, 'policy': challenge.learning_policy,
            'description': challenge.description, 'instructions': challenge.instructions,
            'audit': [a.details for a in self.session.scalars(select(AuditEvent))]})
        self.assertNotIn(FLAG, serialized)
        self.assertNotIn('Servicio2026', serialized)
        self.assertNotIn(flag.flag_hash, serialized)

    async def test_idempotent_reconfiguration_preserves_author_edits_and_flag_hash(self):
        _, challenge = await self.create()
        original_hash = challenge.flags[0].flag_hash
        challenge.name = 'Mi misión editada'
        challenge.instructions = 'Instrucciones propias del instructor.'
        challenge.points = 400
        policy = deepcopy(POLICY)
        policy['duration_minutes'] = 90
        challenge.learning_policy = policy
        self.session.flush()
        before_audits = self.session.scalar(select(func.count()).select_from(AuditEvent))
        report = await configure(self.adapter, URL, FLAG)
        self.assertFalse(report['created'])
        self.assertEqual(challenge.flags[0].flag_hash, original_hash)
        self.assertEqual((challenge.name, challenge.instructions, challenge.points),
            ('Mi misión editada', 'Instrucciones propias del instructor.', 400))
        self.assertEqual(challenge.learning_policy, policy)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Challenge)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ChallengeFlag)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ChallengeGroupAssignment)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(AuditEvent)), before_audits)

    async def test_dry_run_caller_rollback_leaves_database_unchanged(self):
        await self.create()
        self.session.rollback()
        for model in (Challenge, ChallengeFlag, ChallengeGroupAssignment, AuditEvent):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(model)), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(StudentGroup)), 1)

    async def test_rejects_other_scenario_url_or_flag_without_changing_rows(self):
        _, challenge = await self.create()
        for changes in ({'portal_url': 'http://localhost:8095/'}, {'flag_value': FLAG + 'wrong'}):
            with self.subTest(changes=list(changes)):
                with self.assertRaises(ValueError):
                    await configure(self.adapter, changes.get('portal_url', URL), changes.get('flag_value', FLAG))
        challenge.scenario = 'OTHER'
        self.session.flush()
        with self.assertRaises(ValueError):
            await configure(self.adapter, URL, FLAG)
        self.assertEqual(challenge.scenario, 'OTHER')
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ChallengeFlag)), 1)

    async def test_tombstone_prevents_recreation(self):
        self.session.add(AuditEvent(action='challenge.delete', entity_type='challenge',
            entity_id='99', details={'code': CODE, 'name': 'Eliminado'}))
        self.session.flush()
        with self.assertRaisesRegex(ValueError, 'eliminado definitivamente'):
            await configure(self.adapter, URL, FLAG)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Challenge)), 0)

    async def test_missing_or_inactive_group_and_invalid_inputs_leave_no_challenge(self):
        for url, flag, group in [(URL, FLAG, 'MISSING'), ('https://public.example/', FLAG, '45HY'),
                                 (URL, '', '45HY'), (URL, 'x' * 201, '45HY')]:
            with self.subTest(group=group, invalid_url=url != URL, invalid_flag=flag != FLAG):
                with self.assertRaises(ValueError):
                    await configure(self.adapter, url, flag, group_code=group)
        self.session.get(StudentGroup, 1).is_active = False
        self.session.flush()
        with self.assertRaises(ValueError):
            await configure(self.adapter, URL, FLAG)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Challenge)), 0)

    async def test_republishes_and_reassigns_without_resetting_contents(self):
        _, challenge = await self.create()
        assignment = self.session.scalar(select(ChallengeGroupAssignment))
        self.session.delete(assignment)
        challenge.is_published = False
        self.session.flush()
        result = await configure(self.adapter, URL, FLAG)
        self.assertFalse(result['created'])
        self.assertTrue(challenge.is_published)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ChallengeGroupAssignment)), 1)


class CondorConfigurationInputTests(unittest.TestCase):
    def args(self, **overrides):
        return SimpleNamespace(**{'config_stdin': True, 'portal_url': None, 'group': '45HY', **overrides})

    def test_private_stdin_json_and_environment_mode(self):
        value = json.dumps({'portal_url': URL, 'flag_value': FLAG})
        self.assertEqual(read_config(self.args(), stream=io.StringIO(value)), (URL, FLAG, '45HY'))
        self.assertEqual(read_config(self.args(config_stdin=False, portal_url=URL),
            environ={'CONDOR_CHALLENGE_FLAG': FLAG}), (URL, FLAG, '45HY'))

    def test_invalid_or_ambiguous_config_fails_without_echoing_secret(self):
        values = ['[]', '{}', '{', json.dumps({'portal_url': URL, 'flag_value': FLAG, 'extra': FLAG}),
                  json.dumps({'portal_url': URL, 'flag_value': FLAG, 'group_code': 1}), 'x' * 8193]
        for raw in values:
            with self.subTest(kind=raw[:1]):
                with self.assertRaises(ValueError) as raised:
                    read_config(self.args(), stream=io.StringIO(raw))
                self.assertNotIn(FLAG, str(raised.exception))
        with self.assertRaises(ValueError):
            read_config(self.args(portal_url=URL), stream=io.StringIO('{}'))
        with self.assertRaises(ValueError):
            read_config(self.args(config_stdin=False, portal_url=URL), environ={})
