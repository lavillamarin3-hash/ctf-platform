"""Pruebas unitarias del servicio de banderas de la Fase A."""

import unittest

from app.domain.flags.service import FlagService


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


if __name__ == "__main__":
    unittest.main()
