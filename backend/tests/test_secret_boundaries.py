"""Regresiones: respuestas de administración y validación no filtran secretos."""
import json
from copy import deepcopy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.guacamole import guacamole_update_user, public_parameters
from app.main import validation_error_handler
from app.schemas import GuacamoleUserUpdate
from app.guacamole import ManagedGuacamoleAdapter, StubGuacamoleAdapter, GuacamoleApiError
from configure_rdp_display import configure as configure_rdp_display


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
        self.assertNotIn("resize-method", body["parameters"])

    async def test_created_rdp_accepts_resize_and_ssh_is_unchanged(self):
        adapter = object.__new__(ManagedGuacamoleAdapter)
        adapter._api_request = AsyncMock(return_value=None)
        rdp = await adapter.create_connection(name="Desktop", protocol="rdp", hostname="vm.test", port=3389,
                                               username="lab-test", password="example-test-only")
        self.assertEqual(rdp.parameters["resize-method"], "reconnect")
        self.assertEqual(rdp.parameters["password"], "example-test-only")
        ssh = await adapter.create_connection(name="Shell", protocol="ssh", hostname="vm.test", port=22)
        self.assertEqual(ssh.parameters, {"hostname": "vm.test", "port": "22"})
        stub = StubGuacamoleAdapter()
        rdp_stub = await stub.create_connection(name="Desktop", protocol="rdp", hostname="vm.test", port=3389)
        self.assertEqual(rdp_stub.parameters["resize-method"], "reconnect")

    async def test_rdp_edit_defaults_resize_without_losing_parameters_or_attributes(self):
        for resize in (None, "", "display-update", "reconnect", "none"):
            with self.subTest(resize=resize):
                adapter = object.__new__(ManagedGuacamoleAdapter)
                parameters = {"hostname": "vm.test", "port": "3389", "username": "lab-test",
                              "password": "example-test-only", "security": "nla", "width": "1024"}
                if resize is not None:
                    parameters["resize-method"] = resize
                attributes = {"max-connections": "3", "failover-only": "false"}
                adapter._api_request = AsyncMock(side_effect=[
                    {"identifier": "rdp", "attributes": attributes}, parameters, None,
                ])
                await adapter.update_connection("rdp", name="Renamed", protocol="rdp", hostname="vm.test", port=3389)
                body = adapter._api_request.call_args.kwargs["data"]
                self.assertEqual(body["parameters"]["resize-method"], resize or "reconnect")
                self.assertEqual(body["parameters"]["password"], parameters["password"])
                self.assertEqual(body["parameters"]["width"], "1024")
                self.assertEqual(body["parameters"]["security"], "nla")
                self.assertEqual(body["attributes"], attributes)

    async def test_rdp_display_script_is_limited_idempotent_and_keeps_secrets_private(self):
        records = {
            "kali": {"identifier": "kali", "name": "Kali RDP", "protocol": "rdp", "parentIdentifier": "group",
                     "attributes": {"max-connections": "4"},
                     "parameters": {"hostname": "192.168.146.134", "port": "3389", "username": "lab-test",
                                    "password": "example-test-only", "security": "nla", "resize-method": "display-update",
                                    "width": "1024", "height": "768"}},
            "victim": {"identifier": "victim", "name": "Victim RDP", "protocol": "rdp", "attributes": {},
                       "parameters": {"hostname": "192.168.146.137", "port": "3389", "password": "another-test-secret"}},
            "other": {"identifier": "other", "protocol": "rdp", "attributes": {},
                      "parameters": {"hostname": "192.168.146.135", "port": "3389", "width": "800"}},
            "shell": {"identifier": "shell", "protocol": "ssh", "attributes": {},
                      "parameters": {"hostname": "192.168.146.134", "port": "22", "width": "80"}},
        }
        original = deepcopy(records)

        async def request(method, path, *, data=None):
            if path == '/connections':
                return {key: {"identifier": key, "name": value.get("name", ""), "protocol": value["protocol"]}
                        for key, value in records.items()}
            identifier = path.split('/')[2]
            if method == 'GET':
                if path.endswith('/parameters'):
                    return deepcopy(records[identifier]['parameters'])
                detail = deepcopy(records[identifier])
                detail.pop('parameters')
                return detail
            self.assertEqual(method, 'PUT')
            records[identifier] = deepcopy(data)

        adapter = SimpleNamespace(_api_request=AsyncMock(side_effect=request))
        checked = await configure_rdp_display(adapter, apply=False)
        self.assertEqual(records, original)
        self.assertTrue(all(call.args[0] == 'GET' for call in adapter._api_request.await_args_list))
        self.assertEqual({row['host'] for row in checked}, {'192.168.146.134', '192.168.146.137'})
        applied = await configure_rdp_display(adapter, apply=True)
        for identifier in ('kali', 'victim'):
            current = records[identifier]
            self.assertEqual(current['parameters']['resize-method'], 'reconnect')
            self.assertNotIn('width', current['parameters'])
            self.assertNotIn('height', current['parameters'])
            for key, value in original[identifier]['parameters'].items():
                if key not in ('resize-method', 'width', 'height'):
                    self.assertEqual(current['parameters'][key], value)
            self.assertEqual(current['attributes'], original[identifier]['attributes'])
        self.assertEqual(records['kali']['parentIdentifier'], 'group')
        self.assertEqual(records['other'], original['other'])
        self.assertEqual(records['shell'], original['shell'])
        serialized = json.dumps(applied)
        self.assertNotIn('example-test-only', serialized)
        self.assertNotIn('another-test-secret', serialized)
        self.assertTrue(all(set(row) == {'host', 'resize_method', 'width', 'height'} for row in applied))
        adapter._api_request.reset_mock()
        await configure_rdp_display(adapter, apply=True)
        self.assertTrue(all(call.args[0] == 'GET' for call in adapter._api_request.await_args_list))

    async def test_rdp_display_script_aborts_without_preserved_parameters(self):
        adapter = SimpleNamespace(_api_request=AsyncMock(side_effect=[
            {"rdp": {"protocol": "rdp"}}, {"identifier": "rdp", "protocol": "rdp", "attributes": {}}, None,
        ]))
        with self.assertRaises(GuacamoleApiError):
            await configure_rdp_display(adapter, apply=True)
        self.assertTrue(all(call.args[0] == 'GET' for call in adapter._api_request.await_args_list))

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
