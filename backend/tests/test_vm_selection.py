"""LAB-01 no debe elegir una ficha Kali con la IP de la víctima."""

from types import SimpleNamespace
import unittest

from app.services.challenge_runtime import _find_challenge_vm


class Session:
    def __init__(self, labs):
        self.labs = labs

    async def scalars(self, _statement):
        return self

    def unique(self):
        return self

    def all(self):
        return self.labs


class VMSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_lab01_selects_confirmed_linux_victim_not_legacy_kali_duplicate(self):
        wrong = SimpleNamespace(name="lab02", ip_address="192.168.146.137", os="Kali Linux 2026.2", status="ready")
        victim = SimpleNamespace(name="LAB-LNXVICT", ip_address="192.168.146.137", os="Ubuntu Server", status="ready")
        labs = [
            SimpleNamespace(code="LAB-01", name="Reconocimiento SSH controlado", status="ready", vms=[wrong]),
            SimpleNamespace(code="LAB-VICTIMAS", name="Laboratorio de Víctimas", status="ready", vms=[victim]),
        ]
        selected_lab, selected_vm = await _find_challenge_vm(
            Session(labs), SimpleNamespace(code="LAB-01", asset_references=["192.168.146.137", "LAB-01"])
        )
        self.assertIs(selected_lab, labs[1])
        self.assertIs(selected_vm, victim)

    async def test_lab01_fails_closed_when_only_mislabelled_vm_exists(self):
        wrong = SimpleNamespace(name="lab02", ip_address="192.168.146.137", os="Kali Linux", status="ready")
        labs = [SimpleNamespace(code="LAB-01", name="Reto", status="ready", vms=[wrong])]
        self.assertEqual(
            await _find_challenge_vm(Session(labs), SimpleNamespace(code="LAB-01", asset_references=["192.168.146.137"])),
            (None, None),
        )

    async def test_lab01_fails_closed_on_duplicate_confirmed_victim_entries(self):
        victim = SimpleNamespace(name="LAB-LNXVICT", ip_address="192.168.146.137", os="Linux", status="ready")
        labs = [SimpleNamespace(code="LAB-VICTIMAS", name="Víctimas", status="ready", vms=[victim, victim])]
        self.assertEqual(
            await _find_challenge_vm(Session(labs), SimpleNamespace(code="LAB-01", asset_references=["LAB-LNXVICT"])),
            (None, None),
        )


if __name__ == "__main__":
    unittest.main()
