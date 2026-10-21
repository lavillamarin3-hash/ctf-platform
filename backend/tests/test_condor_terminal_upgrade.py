"""Migración explícita de Cóndor sobre SQLite en memoria con FK activadas."""
from copy import deepcopy
from datetime import timedelta
import json
from types import SimpleNamespace
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.core import now_utc, verify_password
from app.models import (
    AuditEvent, Base, Challenge, ChallengeCompletion, ChallengeFlag,
    ChallengeGroupAssignment, ChallengeHintReveal, ChallengeLearningProgress,
    ChallengeRun, StudentGroup, Submission, User,
)
from app.services import external_web
from app.services.condor_catalog import POLICY, TERMINAL_HINTS, configure, upgrade_terminal
from configure_condor_challenge import read_config


FLAG = 'COCIBER{only_ephemeral_terminal_upgrade_test}'
PORTAL = 'http://192.168.146.137:18083/'


class AsyncAdapter:
    def __init__(self, session):
        self.session = session

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, value):
        self.session.add(value)

    async def flush(self):
        self.session.flush()


class CondorTerminalUpgradeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        event.listen(self.engine, 'connect', lambda db, _: db.execute('PRAGMA foreign_keys=ON'))
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.session.close)
        self.session.add_all([
            StudentGroup(id=1, code='45HY', name='verde', is_active=True),
            User(id=1, username='qa-condor-upgrade', role='player', password_hash='!disabled!'),
        ])
        self.session.commit()
        self.adapter = AsyncAdapter(self.session)

    async def create(self):
        await configure(self.adapter, 'http://localhost:8094/', FLAG)
        self.session.commit()
        return self.session.scalar(select(Challenge).where(Challenge.code == external_web.CODE))

    def count(self, model, condition=None):
        query = select(func.count()).select_from(model)
        return self.session.scalar(query.where(condition) if condition is not None else query)

    async def test_upgrade_preserves_static_hash_points_and_custom_policy_values(self):
        challenge = await self.create()
        flag_hash = challenge.flags[0].flag_hash
        policy = deepcopy(POLICY)
        policy.update(duration_minutes=90, expired_points_percent=40)
        for hint, cost in zip(policy['hints'], (5, 15, 20)):
            hint['penalty_percent'] = cost
            hint['content'] = 'Texto anterior del instructor.'
        challenge.learning_policy = policy
        challenge.points = 400
        challenge.name = 'Nombre elegido por el instructor'
        challenge.description = 'Descripción elegida por el instructor.'
        self.session.commit()

        result = await upgrade_terminal(self.adapter, PORTAL)
        self.assertTrue(result['upgraded'])
        self.assertFalse(result['flag_rotated'])
        self.assertTrue(result['terminal_required'])
        self.assertEqual(challenge.asset_references, ['CONDOR-PORTAL:' + PORTAL, 'LAB-KALI'])
        self.assertNotIn('LAB-LNXVICT', challenge.asset_references)
        self.assertEqual((challenge.points, challenge.name, challenge.description),
            (400, 'Nombre elegido por el instructor', 'Descripción elegida por el instructor.'))
        self.assertEqual(challenge.learning_policy['duration_minutes'], 90)
        self.assertEqual(challenge.learning_policy['expired_points_percent'], 40)
        self.assertEqual([h['penalty_percent'] for h in challenge.learning_policy['hints']], [5, 15, 20])
        self.assertEqual(challenge.learning_policy['hints'][0]['content'], TERMINAL_HINTS[0]['content'])
        self.assertEqual(challenge.flags[0].flag_hash, flag_hash)
        self.assertEqual(self.count(ChallengeFlag), 1)
        self.assertEqual(self.count(ChallengeGroupAssignment), 1)
        self.assertIn('terminal SSH de Kali', challenge.instructions)
        payload = json.dumps({'policy': challenge.learning_policy, 'instructions': challenge.instructions,
                              'report': result, 'audits': [row.details for row in self.session.scalars(select(AuditEvent))]})
        for secret in (FLAG, flag_hash, 'admin.condor', 'Servicio2026'):
            self.assertNotIn(secret, payload)

    async def test_upgrade_retains_completed_results_and_private_learning_snapshots(self):
        challenge = await self.create()
        now = now_utc()
        self.session.add(ChallengeRun(id=10, user_id=1, challenge_id=challenge.id,
            status='closed', workspace_strategy=external_web.STRATEGY,
            started_at=now - timedelta(hours=2), expires_at=now - timedelta(hours=1)))
        self.session.flush()
        original = deepcopy(POLICY)
        self.session.add(ChallengeLearningProgress(id=1, user_id=1, challenge_id=challenge.id,
            first_run_id=10, base_points=250, deadline=now - timedelta(hours=1),
            policy_version=2, policy_snapshot=original, is_assisted=False))
        self.session.flush()
        self.session.add_all([
            ChallengeHintReveal(progress_id=1, run_id=10, hint_id=1, penalty_percent=10),
            ChallengeCompletion(user_id=1, challenge_id=challenge.id, awarded_points=175),
            Submission(user_id=1, challenge_id=challenge.id, flag_id=challenge.flags[0].id,
                       submitted_value_hmac='0' * 64, is_correct=True),
        ])
        self.session.commit()
        replacement = 'COCIBER{replacement_only_for_ephemeral_test}'
        result = await upgrade_terminal(self.adapter, PORTAL, flag_value=replacement)
        self.assertTrue(result['flag_rotated'])
        self.assertTrue(verify_password(replacement, challenge.flags[0].flag_hash))
        self.assertFalse(verify_password(FLAG, challenge.flags[0].flag_hash))
        self.assertEqual(self.session.get(ChallengeLearningProgress, 1).policy_snapshot, original)
        self.assertEqual(self.session.get(ChallengeLearningProgress, 1).first_run_id, 10)
        self.assertEqual(self.session.scalar(select(ChallengeCompletion)).awarded_points, 175)
        self.assertEqual(self.session.scalar(select(ChallengeHintReveal)).penalty_percent, 10)
        self.assertEqual(self.count(Submission), 1)
        self.assertEqual(self.session.get(ChallengeRun, 10).status, 'closed')

    async def test_upgrade_blocks_any_active_run_even_when_its_deadline_has_expired(self):
        challenge = await self.create()
        before_refs = list(challenge.asset_references)
        before_policy = deepcopy(challenge.learning_policy)
        self.session.add(ChallengeRun(user_id=1, challenge_id=challenge.id, status='active',
            expires_at=now_utc() - timedelta(minutes=1), workspace_strategy=external_web.STRATEGY))
        self.session.commit()
        with self.assertRaises(HTTPException) as raised:
            await upgrade_terminal(self.adapter, PORTAL)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(challenge.asset_references, before_refs)
        self.assertEqual(challenge.learning_policy, before_policy)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge.condor.terminal_upgrade'), 0)

    async def test_repeated_upgrade_is_idempotent_and_keeps_one_assignment_and_audit(self):
        await self.create()
        first = await upgrade_terminal(self.adapter, PORTAL)
        self.session.commit()
        second = await upgrade_terminal(self.adapter, PORTAL)
        self.assertTrue(first['upgraded'])
        self.assertFalse(second['upgraded'])
        self.assertEqual(self.count(ChallengeGroupAssignment), 1)
        self.assertEqual(self.count(ChallengeFlag), 1)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge.condor.terminal_upgrade'), 1)

    async def test_dry_run_rollback_restores_local_references_and_legacy_policy(self):
        challenge = await self.create()
        before = deepcopy(challenge.learning_policy)
        await upgrade_terminal(self.adapter, PORTAL)
        self.session.rollback()
        self.session.refresh(challenge)
        self.assertEqual(challenge.asset_references, ['CONDOR-PORTAL:http://localhost:8094/'])
        self.assertEqual(challenge.learning_policy, before)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'challenge.condor.terminal_upgrade'), 0)

    async def test_upgrade_cannot_recreate_missing_or_tombstoned_challenge(self):
        with self.assertRaisesRegex(ValueError, 'no crea retos'):
            await upgrade_terminal(self.adapter, PORTAL)
        self.session.add(AuditEvent(action='challenge.delete', entity_type='challenge', entity_id='99',
            details={'code': external_web.CODE}))
        self.session.flush()
        with self.assertRaisesRegex(ValueError, 'eliminado definitivamente'):
            await upgrade_terminal(self.adapter, PORTAL)
        self.assertEqual(self.count(Challenge), 0)

    async def test_invalid_targets_or_groups_do_not_change_existing_challenge(self):
        challenge = await self.create()
        for url, group in [('http://localhost:18083/', '45HY'),
                           ('http://192.168.146.137:8080/', '45HY'),
                           (PORTAL, 'MISSING')]:
            with self.subTest(url=url, group=group):
                with self.assertRaises(ValueError):
                    await upgrade_terminal(self.adapter, url, group)
        self.assertEqual(challenge.asset_references, ['CONDOR-PORTAL:http://localhost:8094/'])

    async def test_preserves_single_hint_cost_instead_of_adding_unconfigured_discount(self):
        challenge = await self.create()
        policy = deepcopy(POLICY)
        policy['hints'] = [dict(policy['hints'][0], penalty_percent=80)]
        challenge.learning_policy = policy
        self.session.commit()
        await upgrade_terminal(self.adapter, PORTAL)
        self.assertEqual(len(challenge.learning_policy['hints']), 1)
        self.assertEqual(challenge.learning_policy['hints'][0]['penalty_percent'], 80)

    async def test_explicit_rotation_is_idempotent_and_audits_never_contain_flags_or_hashes(self):
        challenge = await self.create()
        replacement = 'COCIBER{replacement_only_for_ephemeral_test}'
        first = await upgrade_terminal(self.adapter, PORTAL, flag_value=replacement)
        stored_hash = challenge.flags[0].flag_hash
        self.session.commit()
        second = await upgrade_terminal(self.adapter, PORTAL, flag_value=replacement)
        self.assertTrue(first['flag_rotated'])
        self.assertFalse(second['flag_rotated'])
        self.assertFalse(second['upgraded'])
        self.assertEqual(challenge.flags[0].flag_hash, stored_hash)
        self.assertEqual(self.count(AuditEvent, AuditEvent.action == 'flag.replace'), 1)
        report = json.dumps({'first': first, 'second': second,
            'audit': [row.details for row in self.session.scalars(select(AuditEvent))]})
        for value in (FLAG, replacement, stored_hash):
            self.assertNotIn(value, report)

    async def test_invalid_explicit_rotation_value_leaves_hash_and_references_unchanged(self):
        challenge = await self.create()
        original_hash = challenge.flags[0].flag_hash
        for invalid in ('short', 'x' * 201, 'test\n' * 4, 123):
            with self.subTest(kind=type(invalid).__name__):
                with self.assertRaises(ValueError):
                    await upgrade_terminal(self.adapter, PORTAL, flag_value=invalid)
        self.assertEqual(challenge.flags[0].flag_hash, original_hash)
        self.assertEqual(challenge.asset_references, ['CONDOR-PORTAL:http://localhost:8094/'])


class CondorWorkshopCliTests(unittest.TestCase):
    def test_upgrade_requires_url_and_accepts_optional_private_environment_flag(self):
        args = SimpleNamespace(terminal_workshop=True, config_stdin=False, portal_url=PORTAL, group='45HY')
        self.assertEqual(read_config(args, environ={}), (PORTAL, None, '45HY'))
        self.assertEqual(read_config(args, environ={'CONDOR_CHALLENGE_FLAG': FLAG}), (PORTAL, FLAG, '45HY'))
        args.portal_url = None
        with self.assertRaises(ValueError):
            read_config(args)
        args.portal_url = PORTAL
        args.config_stdin = True
        with self.assertRaises(ValueError):
            read_config(args)
