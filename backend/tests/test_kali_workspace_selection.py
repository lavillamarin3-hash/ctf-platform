from types import SimpleNamespace
import unittest

from fastapi import HTTPException
from app.services import kali_workspace


class KaliWorkspaceSelectionTests(unittest.TestCase):
    def challenge(self, refs):
        return SimpleNamespace(asset_references=refs)

    def test_assigns_blue_and_purple_to_their_fixed_ips(self):
        self.assertEqual(
            kali_workspace.attacker_for(self.challenge(['LAB-KALI-BLUE', 'LAB-LNXVICT'])),
            ('LAB-KALI-BLUE', '10.10.20.12'),
        )
        self.assertEqual(
            kali_workspace.attacker_for(self.challenge(['LAB-KALI-PURPLE', 'LAB-SRVWEB'])),
            ('LAB-KALI-PURPLE', '10.10.20.11'),
        )

    def test_rejects_missing_or_ambiguous_attackers(self):
        self.assertIsNone(kali_workspace.attacker_for(self.challenge(['LAB-SRVWEB'])))
        with self.assertRaises(HTTPException):
            kali_workspace.attacker_for(
                self.challenge(['LAB-KALI-BLUE', 'LAB-KALI-PURPLE', 'LAB-LNXVICT']))


if __name__ == '__main__':
    unittest.main()
