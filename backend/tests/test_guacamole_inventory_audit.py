"""Auditoría no destructiva de conexiones entre CoCiber y Guacamole."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.guacamole import guacamole_inventory_audit, router


class Session:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def scalars(self, _):
        vms = [
            SimpleNamespace(id=1, name="LAB-KALI", ip_address="10.10.20.10",
                            guacamole_connection_id="c-kali"),
            SimpleNamespace(id=2, name="LAB-LNXVICT", ip_address="10.10.30.12",
                            guacamole_connection_id="c-absent"),
            SimpleNamespace(id=3, name="LAB-SRVWEB", ip_address="10.10.30.20",
                            guacamole_connection_id=None),
        ]
        return SimpleNamespace(all=lambda: vms)


class InventoryAuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_audit_reads_remote_connections_without_creating_them(self):
        remote = SimpleNamespace(
            list_connections=AsyncMock(return_value=[
                SimpleNamespace(identifier="c-kali", hostname="10.10.20.10"),
                SimpleNamespace(identifier="extra", hostname="10.10.30.10"),
            ]),
            create_connection=AsyncMock(),
            delete_connection=AsyncMock(),
        )
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            guacamole_admin=remote, session_factory=lambda: Session())))
        with patch("app.api.guacamole.get_settings", return_value=SimpleNamespace(guacamole_mode="real")):
            result = await guacamole_inventory_audit(req, None)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["remote_connections_total"], 2)
        self.assertEqual(result["linked_vm_count"], 1)
        self.assertEqual(result["missing_vm_connections"][0]["vm_name"], "LAB-LNXVICT")
        self.assertEqual(result["unlinked_remote_connections"], 1)
        remote.create_connection.assert_not_awaited()
        remote.delete_connection.assert_not_awaited()

    def test_audit_route_is_get_only(self):
        route = next(r for r in router.routes if r.path == "/api/v1/admin/guacamole/inventory-audit")
        self.assertEqual(route.methods, {"GET"})
