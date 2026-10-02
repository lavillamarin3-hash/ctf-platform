"""Diagnóstico administrativo de solo lectura con dobles de infraestructura."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.api.laboratories import verify_ssh_lab
from app.domain.instances.states import InstanceState
from app.models import ChallengeFlag


class ReadSession:
    def __init__(self, values):
        self.values = list(values)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def scalar(self, statement):
        return self.values.pop(0)


class LabDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        vm = SimpleNamespace(id=6, name="LAB-LNXVICT", ip_address="192.168.146.137", guacamole_connection_id=None)
        flag = ChallengeFlag(id=1, mode="dynamic", template="FLAG{lab-01_{{RAND}}}", flag_order=1, is_active=True)
        challenge = SimpleNamespace(code="LAB-01", flags=[flag])
        pool = SimpleNamespace(state=InstanceState.AVAILABLE.value, run_id=None, user_id=None)
        self.values = [vm, 1, challenge, pool]
        connection = SimpleNamespace(protocol="ssh", hostname=vm.ip_address, identifier="10", name="SSH víctima")
        self.guacamole = SimpleNamespace(list_connections=AsyncMock(return_value=[connection]))
        self.redis = SimpleNamespace(get=AsyncMock(return_value=None), ttl=AsyncMock(return_value=-2))
        self.injector = SimpleNamespace(preflight=AsyncMock(), probe_authentication=AsyncMock())
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            session_factory=lambda: ReadSession(self.values),
            guacamole_admin=self.guacamole, redis=self.redis, flag_injector=self.injector,
        )))
        self.settings = SimpleNamespace(flag_injector_enabled=True, flag_injector_remote_script="/opt/ctf/inject", flag_injector_flag_path="/opt/ctf/flag.txt", flag_injector_ssh_port=22)
        target = patch("app.api.laboratories._find_challenge_vm", new=AsyncMock(return_value=(SimpleNamespace(id=2), vm)))
        self.selector = target.start()
        self.addCleanup(target.stop)

    async def test_reports_ready_without_persisted_guacamole_id_when_ssh_matches_ip(self):
        with patch("app.api.laboratories.get_settings", return_value=self.settings):
            result = await verify_ssh_lab(self.request, None)
        self.assertTrue(result["read_only"])
        self.assertTrue(result["ready_for_dynamic_lab"])
        self.assertFalse(result["database_state"]["vm_has_guacamole_id"])
        self.assertTrue(result["runtime"]["ssh_reachable_from_api"])
        self.assertTrue(result["runtime"]["injector_authenticated"])
        self.assertEqual(result["database_state"]["same_ip_records"], 1)
        self.assertTrue(result["database_state"]["target_selection_matches"])
        self.assertFalse(result["runtime"]["redis_reservation_present"])

    async def test_unreachable_ssh_or_existing_reservation_blocks_ready(self):
        self.injector.preflight.side_effect = OSError("private route")
        self.redis.get.return_value = "167"
        self.redis.ttl.return_value = 501
        with patch("app.api.laboratories.get_settings", return_value=self.settings):
            result = await verify_ssh_lab(self.request, None)
        self.assertFalse(result["ready_for_dynamic_lab"])
        self.assertFalse(result["runtime"]["ssh_reachable_from_api"])
        self.assertIsNone(result["runtime"]["injector_authenticated"])
        self.assertEqual(result["runtime"]["redis_reservation_ttl_seconds"], 501)
        self.assertNotIn("167", str(result))
        self.assertNotIn("private route", str(result))

    async def test_injector_authentication_failure_is_reported_without_error_details(self):
        self.injector.probe_authentication.side_effect = RuntimeError("private credentials detail")
        with patch("app.api.laboratories.get_settings", return_value=self.settings):
            result = await verify_ssh_lab(self.request, None)
        self.assertFalse(result["ready_for_dynamic_lab"])
        self.assertTrue(result["runtime"]["ssh_reachable_from_api"])
        self.assertFalse(result["runtime"]["injector_authenticated"])
        self.assertNotIn("private credentials detail", str(result))

    async def test_diagnostic_rejects_mismatched_challenge_target(self):
        self.selector.return_value = (SimpleNamespace(id=9), SimpleNamespace(id=99))
        with patch("app.api.laboratories.get_settings", return_value=self.settings):
            result = await verify_ssh_lab(self.request, None)
        self.assertFalse(result["ready_for_dynamic_lab"])
        self.assertFalse(result["database_state"]["target_selection_matches"])


if __name__ == "__main__":
    unittest.main()
