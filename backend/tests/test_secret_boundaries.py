"""Regresiones: respuestas de administración y validación no filtran secretos."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.guacamole import guacamole_update_user, public_parameters
from app.main import validation_error_handler
from app.schemas import GuacamoleUserUpdate
from app.guacamole import ManagedGuacamoleAdapter, GuacamoleApiError


class SecretBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_edit_connection_preserves_hidden_parameters(self):
        adapter = object.__new__(ManagedGuacamoleAdapter)
        adapter._api_request = AsyncMock(side_effect=[
            {"identifier": "test", "parameters": {}},
            {"username": "technical-test", "password": "example-test-only", "private-key": "example-test-only"},
            None,
        ])
        await adapter.update_connection("test", name="Renamed", protocol="ssh", hostname="vm.test", port=22)
        body = adapter._api_request.call_args.kwargs["data"]
        self.assertEqual(body["parameters"]["password"], "example-test-only")
        self.assertEqual(body["parameters"]["username"], "technical-test")
        self.assertNotIn("password", public_parameters(body["parameters"]))

    async def test_missing_parameters_aborts_before_overwriting_connection(self):
        adapter = object.__new__(ManagedGuacamoleAdapter)
        adapter._api_request = AsyncMock(side_effect=[{"identifier": "test"}, None])
        with self.assertRaises(GuacamoleApiError):
            await adapter.update_connection("test", name="Renamed", protocol="ssh", hostname="vm.test", port=22)
        self.assertEqual(adapter._api_request.await_count, 2)

    def test_connection_parameters_strip_technical_credentials(self):
        result = public_parameters({"hostname": "vm.test", "port": "22", "password": "secret",
                                    "sftp-password": "secret", "private-key": "secret",
                                    "username": "technical", "passphrase": "secret", "token": "secret"})
        self.assertEqual(result, {"hostname": "vm.test", "port": "22"})

    async def test_validation_response_never_contains_original_input(self):
        response = await validation_error_handler(None, None)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(list(json.loads(response.body)), ["detail"])

    async def test_password_update_audit_contains_only_change_marker(self):
        from unittest.mock import patch
        adapter = SimpleNamespace(update_user=AsyncMock(return_value=SimpleNamespace(username="student", attributes={}, last_active=None)))
        session = AsyncMock()
        context = AsyncMock()
        context.__aenter__.return_value = session
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(guacamole_admin=adapter, session_factory=lambda: context)))
        with patch("app.api.guacamole.write_audit", new_callable=AsyncMock) as audit:
            await guacamole_update_user("student", GuacamoleUserUpdate(password="example-test-only"), request, SimpleNamespace(id=1))
            details = audit.call_args.args[-1]
            self.assertTrue(details["password_changed"])
            self.assertNotIn("password", details)
            self.assertNotIn("example-test-only", json.dumps(details))


if __name__ == "__main__":
    unittest.main()
