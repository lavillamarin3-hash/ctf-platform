"""Ejecuta el filtro real de visibilidad únicamente sobre SQLite efímero en memoria."""

from datetime import timedelta
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.laboratories import list_player_laboratories
from app.api.runs import list_runs
from app.core import now_utc
from app.models import Base, Challenge, ChallengeGroupAssignment, ChallengeRun, GroupMembership, Laboratory, StudentGroup, User, VMAsset


class ReadSession:
    """Adapta solo lectura ORM síncrona al endpoint asíncrono durante esta prueba."""
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, statement):
        return self.session.execute(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)


class RunVisibilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.session.close)
        self.player = User(id=8, username="visibility-test", password_hash="unused-test-value", role="player")
        other = User(id=9, username="other-test", password_hash="unused-test-value", role="player")
        active = StudentGroup(id=1, code="TEST-ACTIVE", name="Test activo", is_active=True)
        inactive = StudentGroup(id=2, code="TEST-INACTIVE", name="Test inactivo", is_active=False)
        self.membership = GroupMembership(group_id=1, user_id=8)
        self.session.add_all([self.player, other, active, inactive, self.membership, GroupMembership(group_id=2, user_id=8)])
        for identifier in range(1, 5):
            self.session.add(Challenge(id=identifier, code=f"TEST-{identifier}", name=f"Test {identifier}",
                description="Test", difficulty="basic", mitre_technique="T0000", points=100,
                is_published=identifier != 3))
        self.session.add_all([
            ChallengeGroupAssignment(challenge_id=1, group_id=1),
            ChallengeGroupAssignment(challenge_id=3, group_id=1),
            ChallengeGroupAssignment(challenge_id=4, group_id=2),
        ])
        now = now_utc()
        for identifier in range(1, 5):
            self.session.add(ChallengeRun(id=identifier, user_id=8, challenge_id=identifier, status="closed",
                                         started_at=now, expires_at=now + timedelta(hours=1)))
        self.session.add(ChallengeRun(id=5, user_id=9, challenge_id=1, status="closed", started_at=now,
                                     expires_at=now + timedelta(hours=1)))
        self.session.commit()
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            session_factory=lambda: ReadSession(self.session),
        )))

    async def test_player_sees_only_own_published_runs_in_current_active_groups(self):
        result = await list_runs(self.request, self.player)
        # Excluye otro propietario, sin asignación, despublicado y grupo inactivo.
        self.assertEqual([run.id for run in result], [1])

    async def test_revoked_membership_hides_previous_runs(self):
        self.session.delete(self.membership)
        self.session.commit()
        self.assertEqual(await list_runs(self.request, self.player), [])

    async def test_admin_and_instructor_keep_full_run_inventory(self):
        for role in ("admin", "instructor"):
            with self.subTest(role=role):
                actor = SimpleNamespace(id=99, role=role)
                result = await list_runs(self.request, actor)
                self.assertEqual({run.id for run in result}, {1, 2, 3, 4, 5})

    async def test_student_laboratories_only_include_confirmed_ready_ips(self):
        challenge = self.session.get(Challenge, 1)
        challenge.asset_references = ["LAB-VICTIMAS"]
        lab = Laboratory(id=21, code="LAB-VICTIMAS", name="Víctimas prueba", status="ready")
        lab.vms = [
            VMAsset(id=31, name="LAB-LNXVICT", ip_address="192.168.146.137", status="ready"),
            VMAsset(id=32, name="LAB-SRVWEB", ip_address="10.10.30.20", status="ready"),
            VMAsset(id=33, name="LAB-LNX-OFF", ip_address="192.168.146.134", status="offline"),
            VMAsset(id=34, name="lab02", ip_address="192.168.146.137", status="ready"),
        ]
        self.session.add(lab)
        self.session.commit()
        result = await list_player_laboratories(self.request, self.player)
        self.assertEqual(len(result), 1)
        self.assertEqual([vm.name for vm in result[0].vms], ["LAB-LNXVICT"])


if __name__ == "__main__":
    unittest.main()
