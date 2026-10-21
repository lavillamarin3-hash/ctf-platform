"""Borrado definitivo: API ASGI y SQLite con claves foráneas reales activadas.

No utiliza Docker, VMs, Redis, credenciales ni bases externas. Las dependencias
de rol se ejecutan por HTTP; solo se sustituye la identidad autenticada.
"""
import json
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.api.challenges import router
from app.core import get_current_user, now_utc
from app.models import (AuditEvent, Base, Challenge, ChallengeCompletion, ChallengeFlag,
                        ChallengeGroupAssignment, ChallengeHintReveal, ChallengeInstance,
                        ChallengeLearningProgress, ChallengeRun, ChallengeRunFlag,
                        GroupMembership, Laboratory, RemoteAccessAssignment, StudentGroup,
                        Submission, User, VMAsset)
from app.services.challenge_deletion import deleted_codes


class SQLiteAsyncSession:
    def __init__(self, owner):
        self.owner = owner
        self.session = Session(owner.engine, expire_on_commit=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.session.close()

    async def scalar(self, statement):
        self.owner.statements.append(statement)
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, value):
        self.session.add(value)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()
        self.owner.commits += 1

    async def rollback(self):
        self.session.rollback()
        self.owner.rollbacks += 1


def add_graph(session, *, challenge_id, code, points, user_id, group_id, vm_id):
    """Dos grafos equivalentes permiten comprobar que solo desaparece el elegido."""
    now = now_utc()
    challenge = Challenge(id=challenge_id, code=code, name='Reto QA ' + code,
        description='Descripción sintética de pruebas.', instructions='', difficulty='Básico',
        category='WEB', mitre_technique='T1110.001', asset_references=['OFFLINE-CASE'],
        points=points, created_by=1, is_published=True)
    session.add(challenge)
    session.flush()
    flag = ChallengeFlag(challenge_id=challenge_id, label='Evidencia', mode='static',
                         flag_hash='hash-privado-no-divulgar', flag_order=1, is_active=True)
    run = ChallengeRun(challenge_id=challenge_id, user_id=user_id, status='closed',
        workspace_strategy='offline_case', started_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1), closed_at=now - timedelta(minutes=50))
    session.add_all([flag, run])
    session.flush()
    progress = ChallengeLearningProgress(user_id=user_id, challenge_id=challenge_id,
        first_run_id=run.id, base_points=points, deadline=run.expires_at, policy_version=1)
    session.add(progress)
    session.flush()
    session.add_all([
        ChallengeRunFlag(run_id=run.id, flag_id=flag.id, flag_hash='hash-por-corrida', fingerprint='qa-only'),
        RemoteAccessAssignment(run_id=run.id, external_reference='qa-' + code,
            launch_url='https://terminal.invalid/', status='revoked', expires_at=run.expires_at),
        ChallengeInstance(challenge_id=challenge_id, vm_asset_id=vm_id, state='disponible'),
        Submission(challenge_id=challenge_id, user_id=user_id, flag_id=flag.id,
            submitted_value_hmac='qa-hmac-no-divulgar', is_correct=True),
        ChallengeCompletion(challenge_id=challenge_id, user_id=user_id, awarded_points=points),
        ChallengeGroupAssignment(challenge_id=challenge_id, group_id=group_id, created_by=1),
        ChallengeHintReveal(progress_id=progress.id, run_id=run.id, hint_id=1, penalty_percent=10),
        AuditEvent(actor_id=1, action='challenge.create', entity_type='challenge',
                   entity_id=str(challenge_id), details={'code': code}),
    ])
    session.flush()
    return challenge, run, progress


class ChallengeDeletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite:///:memory:')
        event.listen(self.engine, 'connect', lambda connection, _: connection.execute('PRAGMA foreign_keys=ON'))
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.commits = self.rollbacks = 0
        self.statements = []
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.state.session_factory = lambda: SQLiteAsyncSession(self)
        self.role = 'admin'

        async def identity():
            return SimpleNamespace(id=1, role=self.role, is_active=True)
        self.app.dependency_overrides[get_current_user] = identity
        with Session(self.engine, expire_on_commit=False) as session:
            session.add_all([
                User(id=1, username='qa-admin', role='admin', password_hash='!disabled!'),
                User(id=2, username='qa-player', role='player', password_hash='!disabled!'),
                StudentGroup(id=1, code='QA-GROUP', name='Grupo QA'),
                Laboratory(id=1, code='QA-LAB', name='Laboratorio QA'),
            ])
            session.flush()
            session.add_all([GroupMembership(group_id=1, user_id=2),
                VMAsset(id=1, laboratory_id=1, name='QA-VM'),
                VMAsset(id=2, laboratory_id=1, name='QA-OTHER-VM')])
            session.flush()
            self.target, self.run, self.progress = add_graph(session, challenge_id=1,
                code='QA-DELETE', points=100, user_id=2, group_id=1, vm_id=1)
            add_graph(session, challenge_id=2, code='QA-KEEP', points=200, user_id=2, group_id=1, vm_id=2)
            session.commit()

    async def http(self, method, path, body=None):
        messages = []
        raw = json.dumps(body).encode() if body is not None else b''
        consumed = False

        async def receive():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {'type': 'http.request', 'body': raw, 'more_body': False}
            return {'type': 'http.disconnect'}

        async def send(message):
            messages.append(message)

        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
            'method': method, 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
            'query_string': b'', 'headers': [(b'content-type', b'application/json')],
            'client': ('127.0.0.1', 1234), 'server': ('testserver', 80)}
        await self.app(scope, receive, send)
        code = next(message['status'] for message in messages if message['type'] == 'http.response.start')
        data = b''.join(message.get('body', b'') for message in messages if message['type'] == 'http.response.body')
        return code, json.loads(data) if data else None

    async def preview(self):
        return await self.http('GET', '/api/v1/challenges/QA-DELETE/deletion-preview')

    async def delete(self, body=None):
        return await self.http('DELETE', '/api/v1/challenges/QA-DELETE/permanent',
                               {'confirm_code': 'QA-DELETE'} if body is None else body)

    def count(self, model):
        with Session(self.engine) as session:
            return session.scalar(select(func.count()).select_from(model))

    async def test_preview_counts_graph_and_points_without_private_values(self):
        status, result = await self.preview()
        self.assertEqual(status, 200)
        self.assertTrue(result['can_delete'])
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['counts']['awarded_points'], 100)
        self.assertEqual(len(result['counts']), 11)
        self.assertTrue(all(value == 1 for name, value in result['counts'].items() if name != 'awarded_points'))
        encoded = json.dumps(result)
        for secret in ('hash-privado', 'hash-por-corrida', 'qa-hmac', 'terminal.invalid'):
            self.assertNotIn(secret, encoded)
        self.assertEqual(self.commits, 0)

    async def test_http_requires_admin_for_preview_and_delete(self):
        for role in ('instructor', 'player', 'guest'):
            self.role = role
            self.assertEqual((await self.preview())[0], 403)
            self.assertEqual((await self.delete())[0], 403)
        self.app.dependency_overrides.clear()
        self.assertEqual((await self.preview())[0], 401)
        self.assertEqual((await self.delete())[0], 401)
        self.assertEqual(self.count(Challenge), 2)

    async def test_requires_exact_code_and_rejects_invalid_body(self):
        for value in ('qa-delete', ' QA-DELETE', 'QA-KEEP', 'QA-DELETE '):
            status, _ = await self.delete({'confirm_code': value})
            self.assertEqual(status, 422)
        for value in ({}, {'confirm_code': 'QA-DELETE', 'all': True}, {'confirm_code': None}):
            self.assertEqual((await self.delete(value))[0], 422)
        self.assertEqual(self.count(Challenge), 2)
        self.assertEqual(self.commits, 0)

    async def test_delete_entire_graph_keeps_other_challenge_users_groups_vms_and_audit(self):
        status, result = await self.delete()
        self.assertEqual(status, 200)
        self.assertTrue(result['deleted'])
        self.assertIsNone(result['warning'])
        for model in (Challenge, ChallengeRun, ChallengeFlag, ChallengeRunFlag,
                      RemoteAccessAssignment, ChallengeInstance, ChallengeHintReveal,
                      ChallengeLearningProgress, Submission, ChallengeCompletion, ChallengeGroupAssignment):
            self.assertEqual(self.count(model), 1, model.__name__)
        for model, count in ((User, 2), (StudentGroup, 1), (GroupMembership, 1),
                             (Laboratory, 1), (VMAsset, 2), (AuditEvent, 3)):
            self.assertEqual(self.count(model), count, model.__name__)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Challenge.code)), 'QA-KEEP')
            self.assertEqual(session.scalar(select(ChallengeCompletion.awarded_points)), 200)
            audit = session.scalar(select(AuditEvent).where(AuditEvent.action == 'challenge.delete'))
            self.assertEqual(audit.actor_id, 1)
            self.assertEqual(audit.details, {'code': result['code'], 'name': result['name'], 'counts': result['counts']})
        challenge_locks = [statement for statement in self.statements
                           if getattr(statement, '_for_update_arg', None) is not None]
        self.assertTrue(challenge_locks)
        self.assertIn('FOR NO KEY UPDATE', str(challenge_locks[0].compile(dialect=postgresql.dialect())))
        self.assertEqual((await self.delete())[0], 404)

    async def test_expired_but_uncleaned_run_blocks_with_no_deletes(self):
        with Session(self.engine) as session:
            run = session.get(ChallengeRun, self.run.id)
            run.status = 'active'
            session.commit()
        status, preview = await self.preview()
        self.assertEqual(status, 200)
        self.assertFalse(preview['can_delete'])
        self.assertEqual(preview['blockers'][0]['type'], 'active_runs')
        self.assertEqual((await self.delete())[0], 409)
        self.assertEqual(self.count(ChallengeCompletion), 2)
        self.assertEqual(self.count(ChallengeRun), 2)
        self.assertEqual(self.commits, 0)

    async def test_rechecks_blockers_after_stale_preview(self):
        self.assertTrue((await self.preview())[1]['can_delete'])
        with Session(self.engine) as session:
            access = session.scalar(select(RemoteAccessAssignment).where(RemoteAccessAssignment.run_id == self.run.id))
            access.status = 'active'
            session.commit()
        self.assertEqual((await self.delete())[0], 409)
        self.assertEqual(self.count(Challenge), 2)

    async def test_pending_instance_cleanup_blocks_even_without_active_run(self):
        with Session(self.engine) as session:
            instance = session.scalar(select(ChallengeInstance).where(ChallengeInstance.challenge_id == 1))
            instance.state = 'error'
            instance.last_error = 'Limpieza pendiente de reintento'
            session.commit()
        result = (await self.preview())[1]
        self.assertEqual(result['blockers'][0]['type'], 'pending_instance_cleanup')
        self.assertEqual((await self.delete())[0], 409)

    async def test_audit_failure_rolls_back_all_graph_deletes(self):
        with patch('app.api.challenges.write_audit', new_callable=AsyncMock,
                   side_effect=RuntimeError('Fallo QA antes de commit')):
            with self.assertRaisesRegex(RuntimeError, 'Fallo QA'):
                await self.delete()
        self.assertEqual(self.rollbacks, 1)
        self.assertEqual(self.commits, 0)
        for model in (Challenge, ChallengeRun, ChallengeFlag, ChallengeHintReveal,
                      Submission, ChallengeCompletion, ChallengeInstance):
            self.assertEqual(self.count(model), 2, model.__name__)

    async def test_archive_endpoint_remains_non_destructive(self):
        status, _ = await self.http('DELETE', '/api/v1/challenges/QA-DELETE')
        self.assertEqual(status, 204)
        self.assertEqual(self.count(Challenge), 2)
        self.assertEqual(self.count(ChallengeCompletion), 2)
        with Session(self.engine) as session:
            self.assertFalse(session.get(Challenge, 1).is_published)

    async def test_deleted_code_persisted_in_audit_tombstone(self):
        await self.delete()
        async with self.app.state.session_factory() as session:
            self.assertEqual(await deleted_codes(session), {'QA-DELETE'})

    async def test_startup_seed_does_not_recreate_deleted_challenge(self):
        from app.services.bootstrap import seed_data
        await self.delete()
        spec = {'code': 'QA-DELETE', 'name': 'No recrear', 'description': 'Retirado permanentemente',
            'instructions': '', 'difficulty': 'Básico', 'category': 'WEB', 'mitre_technique': 'T1110',
            'asset_references': ['OFFLINE-CASE'], 'points': 100, 'is_published': True}
        with patch('app.services.bootstrap.get_settings', return_value=SimpleNamespace(ctf_seed_demo_data=True)), \
             patch('app.services.bootstrap.SEED_CHALLENGES', [spec, {**spec, 'code': 'QA-NEW'}]):
            await seed_data(self.app.state.session_factory)
        with Session(self.engine) as session:
            codes = set(session.scalars(select(Challenge.code)))
        self.assertNotIn('QA-DELETE', codes)
        self.assertIn('QA-NEW', codes)

    async def test_http_catalog_does_not_recreate_deleted_challenge(self):
        from app.services.http_catalog import configure
        with Session(self.engine) as session:
            session.get(Challenge, 1).code = 'ESC-06-WEBAUTH'
            session.commit()
        status, _ = await self.http('DELETE', '/api/v1/challenges/ESC-06-WEBAUTH/permanent',
                                    {'confirm_code': 'ESC-06-WEBAUTH'})
        self.assertEqual(status, 200)
        async with self.app.state.session_factory() as session:
            result = await configure(session, group_code='QA-GROUP')
            await session.commit()
        self.assertEqual(result['published_assigned'], ['ESC-07-EXPOSED'])
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(Challenge.id).where(Challenge.code == 'ESC-06-WEBAUTH')))

    async def test_vm_catalog_ignores_only_explicitly_deleted_codes(self):
        from app.services.vm_catalog import configure
        await self.delete()
        with Session(self.engine) as session:
            session.add(Challenge(code='DFIR-01', name='DFIR QA', description='Descripción sintética',
                difficulty='Medio', category='DFIR', mitre_technique='T1000', points=100,
                asset_references=['DFIR-CASE', 'LAB-KALI']))
            session.commit()
        with patch('app.services.vm_catalog.CATALOG', {'QA-DELETE': (), 'QA-KEEP': ()}):
            async with self.app.state.session_factory() as session:
                result = await configure(session)
                await session.commit()
            self.assertEqual(result['kali_analysis'], 2)
        with patch('app.services.vm_catalog.CATALOG', {'QA-UNEXPECTED-MISSING': ()}):
            async with self.app.state.session_factory() as session:
                with self.assertRaisesRegex(ValueError, 'catálogo completo'):
                    await configure(session)

    async def test_deleted_codes_only_reads_real_deletion_audits(self):
        with Session(self.engine) as session:
            session.add_all([
                AuditEvent(action='challenge.archive', entity_type='challenge', entity_id='x', details={'code': 'ARCHIVED'}),
                AuditEvent(action='challenge.delete', entity_type='other', entity_id='x', details={'code': 'OTHER'}),
                AuditEvent(action='challenge.delete', entity_type='challenge', entity_id='x', details={'code': None}),
            ])
            session.commit()
        async with self.app.state.session_factory() as session:
            self.assertEqual(await deleted_codes(session), set())

    async def test_remote_sync_failure_reports_success_and_warning_after_commit(self):
        with Session(self.engine) as session:
            session.get(Challenge, 1).code = 'ESC-01-RECON'
            session.commit()
        with patch('app.api.challenges._reconcile_esc_guacamole_access', new_callable=AsyncMock,
                   side_effect=RuntimeError('Servicio remoto QA no disponible')) as reconcile:
            status, result = await self.http('DELETE', '/api/v1/challenges/ESC-01-RECON/permanent',
                                            {'confirm_code': 'ESC-01-RECON'})
        self.assertEqual(status, 200)
        self.assertTrue(result['deleted'])
        self.assertIn('sincronización', result['warning'])
        reconcile.assert_awaited_once()
        self.assertEqual(reconcile.call_args.args[1], [1])
        self.assertEqual(self.count(Challenge), 1)
        with Session(self.engine) as session:
            self.assertIsNotNone(session.scalar(select(AuditEvent.id).where(
                AuditEvent.action == 'challenge.delete.sync_pending')))


if __name__ == '__main__':
    unittest.main()
