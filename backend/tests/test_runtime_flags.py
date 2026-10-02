"""Pruebas de resolución dinámica sin modificar PostgreSQL."""

import unittest

from app.domain.challenges.catalog import DEMO_VM_IPS, SEED_CHALLENGES
from app.services.runtime_flags import EXPLICIT_STATIC_VALIDATOR, effective_mode_template, is_effectively_dynamic


class _Flag:
    mode = "static"
    template = None
    validator = "exact_hash"
    is_active = True
    flag_order = 1


class RuntimeFlagsTests(unittest.TestCase):
    def test_lab01_can_be_dynamic_without_persisting_mode_change(self):
        flag = _Flag()
        self.assertTrue(is_effectively_dynamic("LAB-01", flag))
        self.assertEqual(
            effective_mode_template("LAB-01", flag),
            ("dynamic", "FLAG{lab-01_{{USER}}_{{RUN_ID}}_{{RAND}}}"),
        )
        self.assertEqual(flag.mode, "static")
        self.assertIsNone(flag.template)

    def test_other_static_challenges_remain_static(self):
        flag = _Flag()
        self.assertFalse(is_effectively_dynamic("WEB-01", flag))

    def test_admin_explicit_static_lab01_is_not_reinterpreted_as_dynamic(self):
        flag = _Flag()
        flag.validator = EXPLICIT_STATIC_VALIDATOR
        self.assertEqual(effective_mode_template("LAB-01", flag), ("static", None))
        self.assertFalse(is_effectively_dynamic("LAB-01", flag))

    def test_inactive_legacy_flag_does_not_trigger_dynamic_run(self):
        flag = _Flag()
        flag.is_active = False
        self.assertFalse(is_effectively_dynamic("LAB-01", flag))

    def test_current_inventory_and_attack_scenario_seed_are_safe_drafts(self):
        self.assertEqual(DEMO_VM_IPS["Atacantes"], {"192.168.146.134"})
        self.assertEqual(DEMO_VM_IPS["Víctimas"], {"192.168.146.137"})
        scenario = next(item for item in SEED_CHALLENGES if item["code"] == "ESC-01-RECON")
        self.assertFalse(scenario["is_published"])
        self.assertEqual(scenario["asset_references"][0], "LAB-LNXVICT")
        self.assertEqual(scenario["flag_specs"][0]["mode"], "dynamic")


if __name__ == "__main__":
    unittest.main()
