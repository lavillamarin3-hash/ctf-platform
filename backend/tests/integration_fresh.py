"""Pruebas reales PostgreSQL en una base DESECHABLE local *_test.

FRESH_TEST_DATABASE_URL=postgresql+asyncpg://...@127.0.0.1:65439/cociber_refactor_test
python -m unittest discover -s tests -p integration_fresh.py
Nunca conectar esta prueba a Nutanix ni a la base operativa.
"""
import asyncio
from datetime import timedelta
import os
from types import SimpleNamespace
import unittest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.engine import make_url
from ctf.adapters.persistence.models import *
from ctf.adapters.persistence.repository import Repository, now
from ctf.application.admin import create_first_admin
from ctf.domain.laboratory import State, new_flag, flag_hash

URL = os.environ.get("FRESH_TEST_DATABASE_URL", "")


@unittest.skipUnless(URL, "Requiere PostgreSQL desechable local")
class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = make_url(URL)
        assert url.host in ("localhost", "127.0.0.1") and url.database.endswith("_test"), "Solo base local desechable"
        self.repo = Repository(URL)
        async with self.repo.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with self.repo.sessions.begin() as s:
            s.add_all([Role(id=1, name="administrador"), Role(id=3, name="player")])
            await s.flush()
            self.u1, self.u2 = uuid4(), uuid4()
            s.add_all([User(id=uid, username=str(uid), password_hash="test", role=3) for uid in (self.u1, self.u2)])
            self.victim_id = uuid4()
            s.add(Machine(id=self.victim_id, name="LAB-LNXVICT", kind="victima", os="Linux", ip="10.10.30.12", vlan=30, state="ready"))
            s.add(Machine(name="LAB-KALI-BLUE", kind="atacante", os="Linux", ip="10.10.20.12", vlan=20, state="ready"))
            lab = Laboratory(code="LAB-TEST", name="Test", segment="test", state="ready")
            s.add(lab)
            group = Group(code="TEST", name="TEST")
            s.add(group)
            await s.flush()
            for vm in (await s.scalars(select(Machine))).all(): s.add(LabMachine(lab_id=lab.id, machine_id=vm.id))
            self.challenge = uuid4()
            s.add(Challenge(id=self.challenge, code="ESC-02", name="SSH", difficulty="medio", mitre="T1110.001", strategy="SSH-PASSWORD-LAB", victim_id=self.victim_id, points=250, state="published"))
            await s.flush()
            s.add_all([Member(group_id=group.id, user_id=uid) for uid in (self.u1, self.u2)])
            s.add(Assignment(group_id=group.id, challenge_id=self.challenge))

    async def asyncTearDown(self): await self.repo.engine.dispose()

    async def test_two_simultaneous_runs_queue_without_overwrite(self):
        first, second = await asyncio.gather(self.repo.enqueue(self.u1, self.challenge), self.repo.enqueue(self.u2, self.challenge))
        reserved = await asyncio.gather(self.repo.reserve_next({"medio":45}), self.repo.reserve_next({"medio":45}))
        self.assertEqual(sum(r is not None for r in reserved), 1)
        async with self.repo.sessions() as s:
            states = list((await s.scalars(select(Run.state))).all())
        self.assertCountEqual(states, [State.QUEUED, State.RESERVED])

    async def test_flag_is_owned_and_points_awarded_once(self):
        run = await self.repo.enqueue(self.u1, self.challenge)
        await self.repo.reserve_next({"medio":45})
        flag = new_flag("SSH-PASSWORD-LAB")
        await self.repo.activate(run.id, flag_hash(flag), "one")
        with self.assertRaises(Exception): await self.repo.submit(run.id, self.u2, flag)
        wrong = await self.repo.submit(run.id, self.u1, new_flag("SSH-PASSWORD-LAB"))
        self.assertFalse(wrong["correct"])
        result = await self.repo.submit(run.id, self.u1, flag)
        self.assertEqual(result["points"], 250)
        await self.repo.released(run.id)
        second = await self.repo.enqueue(self.u1, self.challenge)
        await self.repo.reserve_next({"medio":45})
        await self.repo.activate(second.id, flag_hash(flag), "two")
        result = await self.repo.submit(second.id, self.u1, flag)
        self.assertEqual(result["points"], 0)
        async with self.repo.sessions() as s:
            ranking = await s.get(Ranking, self.u1)
            self.assertEqual((ranking.points, ranking.completed), (250, 1))

    async def test_cleanup_blocks_next_reservation(self):
        run = await self.repo.enqueue(self.u1, self.challenge)
        await self.repo.reserve_next({"medio":45})
        await self.repo.cleaning(run.id, State.CANCELLED)
        await self.repo.enqueue(self.u2, self.challenge)
        self.assertIsNone(await self.repo.reserve_next({"medio":45}))
        await self.repo.released(run.id)
        self.assertIsNotNone(await self.repo.reserve_next({"medio":45}))

    async def test_bootstrap_cannot_create_second_admin(self):
        await create_first_admin(self.repo, "admin_test", "Only-test-1234567")
        with self.assertRaises(ValueError): await create_first_admin(self.repo, "admin_second", "Only-test-1234567")
        async with self.repo.sessions() as s:
            user = await s.scalar(select(User).where(User.role == 1))
            self.assertTrue(user.must_change_password)
            self.assertTrue(user.password_hash.startswith("$argon2id$"))

    async def test_revoked_assignment_cancels_queue(self):
        from sqlalchemy import delete
        run = await self.repo.enqueue(self.u1, self.challenge)
        async with self.repo.sessions.begin() as s: await s.execute(delete(Assignment))
        self.assertIsNone(await self.repo.reserve_next({"medio":45}))
        saved, *_ = await self.repo.context(run.id)
        self.assertEqual(saved.state, State.RELEASED)

    async def test_laboratory_maintenance_blocks_reservation(self):
        await self.repo.enqueue(self.u1, self.challenge)
        async with self.repo.sessions.begin() as s:
            lab = await s.scalar(select(Laboratory))
            lab.state = 'mantenimiento'
        self.assertIsNone(await self.repo.reserve_next({'medio': 45}))

    async def test_catalog_is_explicit_idempotent_and_drafts_only(self):
        from unittest.mock import AsyncMock, patch
        from ctf.infrastructure.cli import execute
        from ctf.domain.laboratory import SCENARIOS
        from app.domain.challenges.catalog import OPERATIONAL_VM_TARGETS
        async with self.repo.sessions.begin() as s:
            existing = {vm.name for vm in (await s.scalars(select(Machine))).all()}
            for name, ip in OPERATIONAL_VM_TARGETS.items():
                if name not in existing:
                    s.add(Machine(name=name, ip=ip, os='test', kind='atacante' if name.startswith('LAB-KALI') else 'victima', vlan=20 if name.startswith('LAB-KALI') else 30))
        runtime = SimpleNamespace(repo=self.repo, close=AsyncMock())
        with patch('ctf.infrastructure.cli.Runtime', return_value=runtime):
            await execute(SimpleNamespace(command='configure-catalog', apply=False))
            async with self.repo.sessions() as s:
                self.assertEqual(len((await s.scalars(select(Challenge))).all()), 1)
            await execute(SimpleNamespace(command='configure-catalog', apply=True))
            await execute(SimpleNamespace(command='configure-catalog', apply=True))
        async with self.repo.sessions() as s:
            configured = (await s.scalars(select(Challenge).where(Challenge.code.in_([scenario.code for scenario in SCENARIOS])))).all()
            self.assertEqual(len(configured), 5)
            self.assertTrue(all(c.state == 'draft' and not c.pilot_passed for c in configured))

    async def test_http_auth_change_password_and_publication_gate(self):
        import httpx
        from unittest.mock import AsyncMock
        from ctf.infrastructure.main import app
        from ctf.application.admin import hasher
        await create_first_admin(self.repo, "admin_http", "Only-test-1234567")
        cache = SimpleNamespace(login_attempt=AsyncMock(return_value=True), client=SimpleNamespace(exists=AsyncMock(return_value=False)))
        app.state.runtime = SimpleNamespace(repo=self.repo, cache=cache, settings=SimpleNamespace(jwt_secret=SimpleNamespace(get_secret_value=lambda: 'test-secret-' * 10), jwt_expira_minutos=60))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            failed = await client.post('/api/v1/users', json={"username":"forbidden", "password":"Only-test-1234567", "role":1})
            self.assertEqual(failed.status_code, 401)
            self.assertEqual(set(failed.json()), {"error_code", "message", "correlation_id"})
            login = await client.post('/api/v1/auth/login', json={"username":"admin_http", "password":"Only-test-1234567"})
            self.assertEqual(login.status_code, 200, login.text)
            client.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
            self.assertEqual((await client.get('/api/v1/users')).status_code, 403)
            changed = await client.post('/api/v1/auth/password', json={"current":"Only-test-1234567", "new":"Only-test-updated-1234567"})
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertEqual((await client.get('/api/v1/users')).status_code, 401)
            client.headers['Authorization'] = 'Bearer ' + changed.json()['access_token']
            self.assertEqual((await client.get('/api/v1/users')).status_code, 200)
            forbidden = await client.post('/api/v1/users', json={"username":"forbidden", "password":"Only-test-1234567", "role":1})
            self.assertEqual(forbidden.status_code, 422)
            publication = await client.post(f'/api/v1/challenges/{self.challenge}/publish')
            self.assertEqual(publication.status_code, 409)
            self.assertEqual((await client.get('/docs')).status_code, 404)


if __name__ == "__main__": unittest.main()
