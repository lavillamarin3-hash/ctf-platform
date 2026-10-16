"""Las duraciones heredadas del catálogo no contradicen la política editable."""
import unittest

from app.models import Challenge
from app.services.bootstrap import challenge_view


class ChallengeInstructionViewTests(unittest.TestCase):
    def challenge(self, code, scenario, instructions):
        return Challenge(id=1, code=code, scenario=scenario, name='Práctica', description='Ejercicio local',
            instructions=instructions, difficulty='Medio', category='WEB', mitre_technique='T1000',
            asset_references=['OFFLINE-CASE'], points=250, is_published=True, flags=[],
            learning_policy={'duration_minutes': 17, 'expired_points_percent': 40,
                'hints': [{'title': 'Observa', 'content': 'Ayuda privada', 'penalty_percent': 20}]})

    def test_legacy_offline_view_uses_counter_preserves_custom_surroundings_and_does_not_write_row(self):
        original = ('Lee README.txt. Dispones de cuatro horas; otra corrida genera nuevos datos. '
                    'Entrega también tus conclusiones al instructor.')
        challenge = self.challenge('CRY-01', 'OFFLINE-V1', original)
        public = challenge_view(challenge)
        admin = challenge_view(challenge, include_flags=True)
        self.assertNotIn('cuatro horas', public.instructions)
        self.assertIn('contador del reto', public.instructions)
        self.assertIn('conserva el plazo y las ayudas originales', public.instructions)
        self.assertTrue(public.instructions.startswith('Lee README.txt.'))
        self.assertTrue(public.instructions.endswith('Entrega también tus conclusiones al instructor.'))
        self.assertEqual(admin.instructions, public.instructions)
        self.assertEqual(admin.learning_policy.duration_minutes, 17)
        self.assertIsNone(public.learning_policy)
        self.assertEqual(challenge.instructions, original)

    def test_legacy_web_password_view_uses_counter_instead_of_one_hour_without_writing_row(self):
        original = 'Trabaja desde Kali. Las ayudas son opcionales y la cuenta caduca en una hora.'
        challenge = self.challenge('ESC-06-WEBAUTH', 'HTTP-PASSWORD-LAB', original)
        view = challenge_view(challenge)
        self.assertNotIn('caduca en una hora', view.instructions)
        self.assertIn('la cuenta caduca según el plazo configurado', view.instructions)
        self.assertIn('contador del reto', view.instructions)
        self.assertEqual(challenge.instructions, original)

    def test_custom_instructions_and_non_catalog_challenges_are_preserved_exactly(self):
        custom = 'Dispones de cuatro horas para la entrega del informe, fuera del contador de esta práctica.'
        cases = [('CRY-01', 'OFFLINE-V1', custom), ('ESC-06-WEBAUTH', 'HTTP-PASSWORD-LAB', custom),
                 ('CUSTOM-01', 'OFFLINE-V1', 'Dispones de cuatro horas; otra corrida genera nuevos datos.'),
                 ('CRY-01', 'CUSTOM-SCENARIO', 'Dispones de cuatro horas; otra corrida genera nuevos datos.'),
                 ('CUSTOM-01', 'HTTP-PASSWORD-LAB', 'la cuenta caduca en una hora.'),
                 ('ESC-06-WEBAUTH', 'CUSTOM-SCENARIO', 'la cuenta caduca en una hora.')]
        for code, scenario, instructions in cases:
            with self.subTest(code=code, scenario=scenario):
                challenge = self.challenge(code, scenario, instructions)
                self.assertEqual(challenge_view(challenge).instructions, instructions)
                self.assertEqual(challenge.instructions, instructions)
