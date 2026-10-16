"""Pruebas unitarias del servicio de banderas de la Fase A."""

import unittest

from app.domain.flags.service import FlagService
from app.services.challenge_runtime import render_dynamic_flag


class FlagServiceTests(unittest.TestCase):
    def test_generates_expected_shape_and_unique_values(self) -> None:
        service = FlagService()
        first = service.generar_bandera("LAB-01")
        second = service.generar_bandera("LAB-01")

        self.assertTrue(first.startswith("FLAG{lab-01_"))
        self.assertTrue(first.endswith("}"))
        self.assertEqual(len(first), len("FLAG{lab-01_") + 32 + 1)
        self.assertNotEqual(first, second)

    def test_uses_injected_verifier(self) -> None:
        service = FlagService(verifier=lambda value, stored: value == stored)
        self.assertTrue(service.validar_hash("FLAG{demo}", "FLAG{demo}"))
        self.assertFalse(service.validar_hash("FLAG{demo}", "FLAG{other}"))

    def test_default_template_and_compatibility_renderer_keep_random_semantics(self):
        template = 'FLAG{demo_{{USER}}_{{RUN_ID}}_{{RAND}}}'
        service = FlagService()
        first = service.render_template(template, code='OTHER-RETO', username='student', run_id=42)
        second = service.render_template(template, code='OTHER-RETO', username='student', run_id=42)
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith('FLAG{demo_student_42_'))
        wrapper_first = render_dynamic_flag(template, code='OTHER-RETO', username='student', run_id=42)
        wrapper_second = render_dynamic_flag(template, code='OTHER-RETO', username='student', run_id=42)
        self.assertNotEqual(wrapper_first, wrapper_second)


if __name__ == "__main__":
    unittest.main()
