"""Tests aislados: no requieren acceso a Nutanix."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.guacamole_preflight import connection_target, check_connection


class ConnectionPreflightTests(unittest.IsolatedAsyncioTestCase):
    def item(self, host="10.10.30.12", protocol="ssh", port="22"):
        return SimpleNamespace(hostname=host, protocol=protocol, port=port)

    def test_known_ssh_and_rdp(self):
        self.assertEqual(connection_target(self.item()), ("10.10.30.12", 22, "ssh"))
        self.assertEqual(connection_target(self.item("10.10.30.10", "rdp", "3389")),
                         ("10.10.30.10", 3389, "rdp"))

    def test_rejects_arbitrary_hosts_dns_and_wrong_ports(self):
        for item in (self.item("127.0.0.1"), self.item("example.org"),
                     self.item("10.10.30.99"), self.item(port="80"),
                     self.item("10.10.30.20", "vnc", "5900")):
            with self.subTest(item=item), self.assertRaises(ValueError):
                connection_target(item)

    async def test_tcp_success_only_reports_reachability(self):
        writer = AsyncMock()
        writer.close = unittest.mock.Mock()
        with patch("app.services.guacamole_preflight.asyncio.open_connection",
                   new_callable=AsyncMock, return_value=(object(), writer)):
            result = await check_connection(self.item())
        self.assertTrue(result["reachable"])
        self.assertIn("Falta verificar", result["message"])

    async def test_tcp_failure_is_not_authenticated(self):
        with patch("app.services.guacamole_preflight.asyncio.open_connection",
                   new_callable=AsyncMock, side_effect=OSError()):
            result = await check_connection(self.item())
        self.assertFalse(result["reachable"])
