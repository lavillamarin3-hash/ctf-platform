"""Pruebas de resolución dinámica sin modificar PostgreSQL."""

import unittest

from app.services.runtime_flags import effective_mode_template, is_effectively_dynamic


class _Flag:
    mode = "static"
    template = None
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


if __name__ == "__main__":
    unittest.main()
