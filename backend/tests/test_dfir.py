import json
import hashlib
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.api import runs
from app.core import now_utc, verify_password
from app.domain.challenges.dfir import build_case, matches_answer
from app.domain.challenges.catalog import DFIR_DRAFT
from app.models import Challenge, ChallengeFlag, ChallengeRunFlag
from app.schemas import ChallengeCreate, SubmissionRequest
from app.services import dfir_runtime
from test_run_lifecycle import MemorySession


class DfirCaseTests(unittest.TestCase):
    def test_solver_uses_only_public_evidence_and_finds_one_solution(self):
        for index in range(100):
            public, private = build_case(str(index))
            beacon = public['calibration'][0]
            delta = datetime.fromisoformat(beacon['auth_clock']) - datetime.fromisoformat(beacon['reference_utc'])
            auth = json.loads(public['files']['auth.json'])
            http = json.loads(public['files']['http.json'])
            net = json.loads(public['files']['network.json'])
            candidates = []
            for a in auth:
                for h in http:
                    for n in net:
                        if (a['result'] == 'success' and a['mfa'] == 'bypassed' and a['session'] == h['session']
                            and h['status'] == 200 and h['bytes'] > 500000 and h['request'] == n['request']
                            and n['destination'] == '203.0.113.77' and h['bytes'] == n['bytes']):
                            candidates.append(dict(session=a['session'], user=a['user'], request=h['request'],
                                                   destination=n['destination'], auth_utc=(datetime.fromisoformat(a['time'])-delta).isoformat()))
            self.assertEqual(candidates, [private])
            self.assertTrue(matches_answer(private, candidates[0]))
            for name, data in public['files'].items():
                self.assertEqual(public['sha256'][name], hashlib.sha256(data.encode()).hexdigest())
            self.assertNotIn('FLAG{', json.dumps(public))

    def test_timestamp_and_wrong_answer(self):
        _, expected = build_case('seed')
        self.assertTrue(matches_answer(expected, {**expected, 'auth_utc': expected['auth_utc'].replace('+00:00', 'Z')}))
        self.assertFalse(matches_answer(expected, {**expected, 'auth_utc': expected['auth_utc'][:-6]}))
        self.assertFalse(matches_answer(expected, {**expected, 'session': 'other'}))

    def test_draft_is_editable_and_unpublished(self):
        draft = ChallengeCreate(**{k:v for k,v in DFIR_DRAFT.items() if k != 'flag_specs'})
        self.assertFalse(draft.is_published)


class DfirLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=8, username='analyst', role='player')
        self.flag = ChallengeFlag(id=11, mode='dynamic', is_active=True, flag_order=1)
        self.challenge = Challenge(id=1, code='DFIR-01', points=500, is_published=True, asset_references=['DFIR-CASE'], flags=[self.flag])
        for target in ('app.api.runs.check_rate_limit', 'app.api.runs.write_audit', 'app.services.dfir_runtime.write_audit'):
            patcher = patch(target, new=AsyncMock()); patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(runs, '_assigned', new=AsyncMock(return_value=True)); patcher.start(); self.addCleanup(patcher.stop)

    def request(self, session):
        return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: session, redis=SimpleNamespace(publish=AsyncMock()), sockets=SimpleNamespace(broadcast=AsyncMock()))))

    def run_record(self):
        return SimpleNamespace(id=101, user_id=8, challenge_id=1, status='active', workspace_strategy='dfir_case',
                               started_at=now_utc(), expires_at=now_utc()+timedelta(hours=2), assignment=None)

    async def test_start_reuse_close_reopen_without_vm_or_guacamole(self):
        session = MemorySession([self.challenge, None])
        result = await runs.start_challenge('DFIR-01', self.request(session), self.user)
        self.assertEqual(result.workspace_strategy, 'dfir_case')
        persisted = next(x for x in session.added if isinstance(x, ChallengeRunFlag))
        record = self.run_record()
        self.assertTrue(verify_password(dfir_runtime.flag_for(record), persisted.flag_hash))
        reused = await runs.start_challenge('DFIR-01', self.request(MemorySession([self.challenge, record])), self.user)
        self.assertEqual(reused.id, 101)
        await runs._cleanup_run(self.request(MemorySession()), MemorySession(), record, self.challenge, status='closed')
        self.assertEqual(record.status, 'closed')
        reopened = await runs.start_challenge('DFIR-01', self.request(MemorySession([self.challenge, None], run_id=102)), self.user)
        self.assertNotEqual(dfir_runtime.flag_for(record), dfir_runtime.flag_for(SimpleNamespace(id=reopened.id, user_id=8)))
        self.assertNotEqual(dfir_runtime.case_for(record), dfir_runtime.case_for(SimpleNamespace(id=reopened.id, user_id=8)))

    async def test_bundle_answer_and_closed_expired_unassigned_access(self):
        record = self.run_record()
        def session():
            return MemorySession([record], objects={(Challenge, 1): self.challenge})
        bundle = await runs.get_dfir_case(101, self.request(session()), self.user)
        self.assertEqual(bundle.headers['cache-control'], 'no-store')
        _, answer = dfir_runtime.case_for(record)
        correct = await runs.answer_dfir_case(101, runs.DfirAnswer(**answer), self.request(session()), self.user)
        self.assertEqual(json.loads(correct.body)['flag'], dfir_runtime.flag_for(record))
        incorrect = await runs.answer_dfir_case(101, runs.DfirAnswer(**{**answer, 'session':'bad'}), self.request(session()), self.user)
        self.assertIsNone(json.loads(incorrect.body)['flag'])
        record.status = 'closed'
        with self.assertRaises(HTTPException): await runs._dfir_run(session(), 101, self.user)
        record.status = 'active'; record.expires_at = now_utc()-timedelta(seconds=1)
        with self.assertRaises(HTTPException): await runs._dfir_run(session(), 101, self.user)
        record.expires_at = now_utc()+timedelta(hours=1)
        with patch.object(runs, '_assigned', new=AsyncMock(return_value=False)):
            with self.assertRaises(HTTPException): await runs._dfir_run(session(), 101, self.user)
        with self.assertRaises(HTTPException): await runs._dfir_run(MemorySession([None]), 999, self.user)

    async def test_standard_flag_submission_awards_500(self):
        record = self.run_record()
        from app.core import hash_password
        stored = SimpleNamespace(flag_hash=hash_password(dfir_runtime.flag_for(record)))
        session = MemorySession([self.challenge, record, stored, None], scalar_lists=[[]])
        with patch.object(runs, 'ranking_rows', new=AsyncMock(return_value=[])):
            result = await runs.submit_flag('DFIR-01', SubmissionRequest(value=dfir_runtime.flag_for(record)), self.request(session), self.user)
        self.assertTrue(result.correct)
        self.assertEqual(result.awarded_points, 500)
