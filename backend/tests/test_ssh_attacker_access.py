"""SSH practice: one selected Kali host with SSH and RDP, never the victim.

All objects and credentials are synthetic. No real VMs or Guacamole modified.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import HTTPException
from app.services import kali_workspace
from app.services.challenge_runtime import _ssh_kali_connection_ids


def vm(name, ip, lab_id=3, status="ready"):
    return SimpleNamespace(id=11, name=name, ip_address=ip, status=status, laboratory_id=lab_id)


def challenge(attacker):
    return SimpleNamespace(code="ESC-02-BRUTEFORCE", asset_references=[attacker, "LAB-LNXVICT"])


class VMRows:
    def __init__(self, vms):
        self.vms = vms

    def all(self):
        return self.vms


class FakeSession:
    def __init__(self, vms):
        self.vms = vms

    async def scalars(self, query):
        return VMRows(self.vms)

    async def get(self, model, id):
        return SimpleNamespace(id=id, status="ready")


def connection(identifier, protocol, ip):
    return SimpleNamespace(identifier=identifier, protocol=protocol, hostname=ip)


class SshAttackerTests(unittest.IsolatedAsyncioTestCase):
    async def test_kali_blue_offers_ssh_and_rdp_without_victim_access(self):
        selected = vm("LAB-KALI-BLUE", "10.10.20.12")
        remote = [connection("ssh-blue", "ssh", "10.10.20.12"),
                  connection("rdp-blue", "rdp", "10.10.20.12"),
                  connection("ssh-victim", "ssh", "10.10.30.12")]
        admin = SimpleNamespace(
            list_connections=AsyncMock(return_value=remote),
            get_user_permissions=AsyncMock(return_value={
                "connectionPermissions": {
                    "ssh-blue": ["READ"], "rdp-blue": ["READ"],
                    "ssh-victim": ["READ"]
                },
            }),
        )
        app = SimpleNamespace(state=SimpleNamespace(guacamole_admin=admin))
        actual, targets = await kali_workspace.context(
            app, FakeSession([selected]), SimpleNamespace(username="student"), challenge("LAB-KALI-BLUE")
        )
        self.assertIs(actual, selected)
        self.assertEqual(targets, {"ssh": "ssh-blue", "rdp": "rdp-blue"})
        self.assertNotIn("ssh-victim", targets.values())

    async def test_unshared_rdp_never_displayed(self):
        selected = vm("LAB-KALI-BLUE", "10.10.20.12")
        app = SimpleNamespace(state=SimpleNamespace(guacamole_admin=SimpleNamespace(
            list_connections=AsyncMock(return_value=[
                connection("ssh-blue", "ssh", "10.10.20.12"),
                connection("rdp-blue", "rdp", "10.10.20.12"),
            ]),
            get_user_permissions=AsyncMock(return_value={
                "connectionPermissions": {"ssh-blue": ["READ"]}
            }),
        )))
        _, targets = await kali_workspace.context(
            app, FakeSession([selected]), SimpleNamespace(username="student"), challenge("LAB-KALI-BLUE")
        )
        self.assertEqual(targets, {"ssh": "ssh-blue"})

    def test_duplicate_protocol_is_not_used(self):
        vms = [vm("LAB-KALI-BLUE", "10.10.20.12")]
        labs = [SimpleNamespace(id=3, status="ready")]
        remote = [connection("a", "ssh", "10.10.20.12"), connection("b", "ssh", "10.10.20.12"),
                  connection("rdp", "rdp", "10.10.20.12")]
        self.assertEqual(_ssh_kali_connection_ids(challenge("LAB-KALI-BLUE"), vms, labs, remote),
                         {"rdp"})

    def test_invalid_attacker_never_selects_victim_or_typo(self):
        with self.assertRaises(HTTPException):
            kali_workspace.selected_attacker(SimpleNamespace(
                asset_references=["LAB-KALI", "LAB-KALI-BLUE"]))
        self.assertEqual(kali_workspace.selected_attacker(challenge("LAB-KALI-BLUE")), "LAB-KALI-BLUE")


if __name__ == "__main__":
    unittest.main()
