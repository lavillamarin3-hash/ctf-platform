"""ESC usa Guacamole para Kali, nunca para entregar la víctima al estudiante."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, call, patch

from app.api import groups
from app.models import Challenge, Laboratory, StudentGroup, User, VMAsset
from app.services import challenge_runtime as runtime
from app.services.challenge_runtime import (
    _guacamole_access_references,
    _sync_guacamole_group_permissions,
    _sync_player_guacamole_permissions,
)


class Rows:
    def __init__(self, values):
        self.values = values

    def unique(self):
        return self

    def all(self):
        return self.values


class Session:
    def __init__(self, challenge, vms, labs):
        self.rows = iter(([challenge], vms, labs))
        self.queries = []
        self.user = SimpleNamespace(id=7, username="student-fixture", role="player")
        self.group = SimpleNamespace(id=3, code="GROUP", guacamole_group_identifier="GROUP")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, model, identifier):
        return self.user if model is User else self.group if model is StudentGroup else None

    async def scalars(self, statement):
        self.queries.append(statement)
        return Rows(next(self.rows))


class EscPermissionsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.challenge = Challenge(
            id=9, code="ESC-01-RECON", is_published=True,
            asset_references=["LAB-LNXVICT", "LAB-KALI"],
        )
        self.vms = [
            SimpleNamespace(name="LAB-LNXVICT", ip_address="192.168.146.137",
                            guacamole_connection_id="victim-ssh", laboratory_id=2, status="ready"),
            SimpleNamespace(name="LAB-KALI", ip_address="192.168.146.134",
                            guacamole_connection_id="kali-ssh", laboratory_id=1, status="ready"),
        ]
        self.connections = [
            SimpleNamespace(identifier="victim-ssh", hostname="192.168.146.137", protocol="ssh"),
            SimpleNamespace(identifier="kali-ssh", hostname="192.168.146.134", protocol="ssh"),
            SimpleNamespace(identifier="kali-rdp", hostname="192.168.146.134", protocol="rdp"),
        ]
        self.labs = [SimpleNamespace(id=1, code="LAB-ATACANTES", name="Atacantes", status="ready"),
                     SimpleNamespace(id=2, code="LAB-VICTIMAS", name="Víctimas", status="ready")]
        self.guac = SimpleNamespace(
            list_connections=AsyncMock(return_value=self.connections),
            patch_user_permissions=AsyncMock(),
            get_user_group_permissions=AsyncMock(return_value={"connectionPermissions": {}}),
            patch_user_group_permissions=AsyncMock(),
        )

    def request(self, session):
        return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            session_factory=lambda: session, guacamole_admin=self.guac,
        )))

    async def test_player_sync_grants_only_kali_and_queries_published_challenges(self):
        session = Session(self.challenge, self.vms, self.labs)
        await _sync_player_guacamole_permissions(self.request(session), 7)
        self.assertEqual(self.guac.patch_user_permissions.await_args.kwargs["connection_permissions"],
                         {"kali-ssh": ["READ"], "kali-rdp": ["READ"]})
        self.assertIn("is_published IS true", str(session.queries[0]))

    async def test_group_sync_grants_only_kali_and_queries_published_challenges(self):
        session = Session(self.challenge, self.vms, self.labs)
        await _sync_guacamole_group_permissions(self.request(session), 3)
        self.assertEqual(self.guac.patch_user_group_permissions.await_args.kwargs["connection_permissions"],
                         {"kali-ssh": ["READ"], "kali-rdp": ["READ"]})
        self.assertIn("is_published IS true", str(session.queries[0]))

    async def test_duplicate_kali_ip_does_not_grant_attacker_or_victim_access(self):
        self.vms.append(SimpleNamespace(name="legacy-duplicate", ip_address="192.168.146.134",
                                         guacamole_connection_id=None, laboratory_id=1, status="ready"))
        session = Session(self.challenge, self.vms, self.labs)
        await _sync_player_guacamole_permissions(self.request(session), 7)
        self.assertEqual(self.guac.patch_user_permissions.await_args.kwargs["connection_permissions"], {})

    async def assert_esc_not_granted(self):
        await _sync_player_guacamole_permissions(
            self.request(Session(self.challenge, self.vms, self.labs)), 7,
        )
        self.assertEqual(self.guac.patch_user_permissions.await_args.kwargs["connection_permissions"], {})
        await _sync_guacamole_group_permissions(
            self.request(Session(self.challenge, self.vms, self.labs)), 3,
        )
        self.assertEqual(self.guac.patch_user_group_permissions.await_args.kwargs["connection_permissions"], {})

    async def test_missing_esc_reference_does_not_grant_kali_access(self):
        for refs in (["LAB-LNXVICT"], ["LAB-KALI"]):
            with self.subTest(refs=refs):
                self.challenge.asset_references = refs
                await self.assert_esc_not_granted()

    async def test_missing_or_ambiguous_victim_does_not_grant_kali_access(self):
        victim = self.vms.pop(0)
        await self.assert_esc_not_granted()
        self.vms.insert(0, victim)
        self.vms.append(SimpleNamespace(name="legacy-duplicate", ip_address="192.168.146.137",
                                         guacamole_connection_id=None, laboratory_id=2, status="ready"))
        await self.assert_esc_not_granted()

    async def test_unready_victim_lab_does_not_grant_kali_access(self):
        self.labs[1].status = "maintenance"
        await self.assert_esc_not_granted()

    def test_lab01_reference_policy_is_unchanged(self):
        lab = Challenge(code="LAB-01", asset_references=["LAB-LNXVICT"])
        self.assertEqual(_guacamole_access_references(lab), ["LAB-LNXVICT"])
        self.assertEqual(_guacamole_access_references(self.challenge), ["LAB-KALI"])


class EscAssignmentSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_esc_assignment_keeps_group_only_sync(self):
        challenge = SimpleNamespace(id=9, code="LAB-01", is_published=True)
        group = SimpleNamespace(id=3)
        session = AsyncMock()
        session.add = Mock()
        session.scalar.side_effect = [challenge, None]
        session.get.return_value = group
        context = AsyncMock()
        context.__aenter__.return_value = session
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: context)))
        with patch.object(groups, "write_audit", new_callable=AsyncMock), \
             patch.object(groups, "_group_view", new_callable=AsyncMock), \
             patch.object(groups, "_sync_guacamole_group_permissions", new_callable=AsyncMock) as group_sync, \
             patch.object(groups, "_reconcile_esc_guacamole_access", new_callable=AsyncMock) as reconcile:
            await groups.assign_challenge_group(challenge.code, group.id, request, SimpleNamespace(id=1))
        group_sync.assert_awaited_once_with(request, group.id)
        reconcile.assert_not_awaited()

    async def test_assign_and_unassign_sync_existing_group_members(self):
        challenge = SimpleNamespace(id=9, code="ESC-01-RECON", is_published=True)
        group = SimpleNamespace(id=3)
        actor = SimpleNamespace(id=1)
        for action in ("assign", "unassign"):
            with self.subTest(action=action):
                session = AsyncMock()
                session.add = Mock()
                session.scalar.side_effect = [challenge, None if action == "assign" else SimpleNamespace(id=4)]
                session.get.return_value = group
                context = AsyncMock()
                context.__aenter__.return_value = session
                request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: context)))
                with patch.object(groups, "write_audit", new_callable=AsyncMock), \
                     patch.object(groups, "_group_view", new_callable=AsyncMock), \
                     patch.object(groups, "_reconcile_esc_guacamole_access", new_callable=AsyncMock) as reconcile:
                    if action == "assign":
                        await groups.assign_challenge_group(challenge.code, group.id, request, actor)
                    else:
                        await groups.unassign_challenge_group(challenge.code, group.id, request, actor)
                reconcile.assert_awaited_once_with(request, [group.id])

    async def test_assign_and_unassign_propagate_reconciliation_failure(self):
        challenge = SimpleNamespace(id=9, code="ESC-01-RECON", is_published=True)
        group = SimpleNamespace(id=3)
        actor = SimpleNamespace(id=1)
        for action in ("assign", "unassign"):
            with self.subTest(action=action):
                session = AsyncMock()
                session.add = Mock()
                session.scalar.side_effect = [challenge, None if action == "assign" else SimpleNamespace(id=4)]
                session.get.return_value = group
                context = AsyncMock()
                context.__aenter__.return_value = session
                request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: context)))
                with patch.object(groups, "write_audit", new_callable=AsyncMock), \
                     patch.object(groups, "_reconcile_esc_guacamole_access", new_callable=AsyncMock,
                                  side_effect=RuntimeError("Guacamole no disponible")) as reconcile:
                    with self.assertRaisesRegex(RuntimeError, "Guacamole no disponible"):
                        if action == "assign":
                            await groups.assign_challenge_group(challenge.code, group.id, request, actor)
                        else:
                            await groups.unassign_challenge_group(challenge.code, group.id, request, actor)
                reconcile.assert_awaited_once_with(request, [group.id])

    async def test_reconcile_attempts_group_and_members_for_every_group_after_failure(self):
        request = SimpleNamespace()
        group_error = RuntimeError("grupo falló")
        with patch.object(runtime, "_sync_guacamole_group_permissions", new_callable=AsyncMock,
                          side_effect=[group_error, None]) as group_sync, \
             patch.object(runtime, "_sync_group_members_guacamole_permissions", new_callable=AsyncMock,
                          side_effect=[None, RuntimeError("miembro falló")]) as members_sync:
            with self.assertRaisesRegex(RuntimeError, "grupo falló"):
                await runtime._reconcile_esc_guacamole_access(request, [3, 4])
        self.assertEqual(group_sync.await_args_list, [call(request, 3), call(request, 4)])
        self.assertEqual(members_sync.await_args_list, [call(request, 3), call(request, 4)])

    async def test_member_failure_does_not_skip_other_members(self):
        session = AsyncMock()
        session.scalars.return_value = SimpleNamespace(all=lambda: [7, 8])
        context = AsyncMock()
        context.__aenter__.return_value = session
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: context)))
        with patch.object(runtime, "_sync_player_guacamole_permissions", new_callable=AsyncMock,
                          side_effect=[RuntimeError("primer miembro falló"), None]) as sync_player:
            with self.assertRaisesRegex(RuntimeError, "primer miembro falló"):
                await runtime._sync_group_members_guacamole_permissions(request, 3)
        self.assertEqual(sync_player.await_args_list, [call(request, 7), call(request, 8)])


if __name__ == "__main__":
    unittest.main()
