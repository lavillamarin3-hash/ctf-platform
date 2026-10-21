"""Las URLs son datos de navegación; no se resuelven ni se consultan."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.services import external_web


class ExternalWebTests(unittest.TestCase):
    def challenge(self, references=None, **kwargs):
        return SimpleNamespace(code=external_web.CODE, scenario=external_web.SCENARIO,
            name='Operación Cóndor: acceso al centro de mando',
            asset_references=references or [external_web.ASSET_PREFIX + 'http://localhost:8094/'], **kwargs)

    def test_accepts_only_explicit_local_or_private_targets_without_dns(self):
        valid = {
            'http://LOCALHOST:8094': 'http://localhost:8094/',
            'https://condor.lab': 'https://condor.lab/',
            'http://192.168.146.150:8080/': 'http://192.168.146.150:8080/',
            'http://10.2.0.5/portal': 'http://10.2.0.5/portal',
            'http://172.16.0.1/': 'http://172.16.0.1/',
            'http://127.0.0.2/': 'http://127.0.0.2/',
            'http://[::1]:8094/': 'http://[::1]:8094/',
            'https://[fd10::5]/': 'https://[fd10::5]/',
        }
        with patch('socket.getaddrinfo', side_effect=AssertionError('No se permite resolver DNS')) as resolve:
            for supplied, expected in valid.items():
                with self.subTest(url=supplied):
                    self.assertEqual(external_web.normalize_portal_url(supplied), expected)
            resolve.assert_not_called()

    def test_rejects_public_ambiguous_or_credential_bearing_targets(self):
        invalid = [None, '', 'ftp://localhost/', '//localhost/', 'javascript:alert(1)',
            'http://example.org/', 'http://192.168.146.150.example.org/',
            'http://localhost.example.org/', 'http://169.254.169.254/', 'http://0.0.0.0/',
            'http://8.8.8.8/', 'http://203.0.113.77/', 'http://[2001:db8::1]/',
            'http://[fe80::1]/', 'http://224.0.0.1/', 'http://localhost:0/',
            'http://localhost:70000/', 'http://user:secret@localhost/',
            'http://localhost/?token=private', 'http://localhost/#private',
            'http://local host/', 'http://localhost/\nheader', 'http://localhost\\@example.org/',
            'http://[fe80::1%25ens33]/', 'http://2130706433/', 'http://localhost/' + 'a' * 1024]
        for value in invalid:
            with self.subTest(url=value):
                with self.assertRaises(ValueError):
                    external_web.normalize_portal_url(value)

    def test_requires_exact_challenge_and_one_portal_reference(self):
        self.assertTrue(external_web.supports(self.challenge()))
        wrong = self.challenge()
        wrong.scenario = 'OTHER'
        self.assertFalse(external_web.supports(wrong))
        for challenge in [wrong, self.challenge(['LAB-KALI']), self.challenge([
                external_web.ASSET_PREFIX + 'http://localhost:8094/',
                external_web.ASSET_PREFIX + 'http://localhost:8095/'])]:
            with self.assertRaises(ValueError):
                external_web.portal_url(challenge)

    def test_info_labels_local_and_private_vm_without_login_secrets(self):
        run = SimpleNamespace(id=1)
        local = external_web.info(run, self.challenge())
        self.assertEqual(local['mode'], 'local')
        self.assertEqual(local['portal_url'], 'http://localhost:8094/')
        self.assertIn('Cerrar el reto no apaga', local['note'])
        self.assertEqual(set(local), {'title', 'portal_url', 'mode', 'objective', 'note'})
        for value in ('http://192.168.146.150:8080/', 'http://condor.lab/'):
            info = external_web.info(run, self.challenge([external_web.ASSET_PREFIX + value]))
            self.assertEqual(info['mode'], 'vm')

    def test_terminal_metadata_exposes_only_host_and_scan_scope_before_discovery(self):
        challenge = self.challenge([external_web.ASSET_PREFIX + 'http://192.168.146.137:18083/', 'LAB-KALI'])
        self.assertTrue(external_web.requires_terminal(challenge))
        info = external_web.info(SimpleNamespace(id=1), challenge)
        self.assertEqual(info['mode'], 'vm')
        self.assertTrue(info['terminal_required'])
        self.assertEqual(info['target_host'], '192.168.146.137')
        self.assertEqual(info['port_scope'], '18080-18090')
        self.assertNotIn('portal_url', info)
        self.assertNotIn('18083', str(info))
        self.assertNotIn('admin.condor', str(info))
        self.assertNotIn('password', info)
        self.assertFalse(external_web.requires_terminal(self.challenge()))

    def test_terminal_opt_in_rejects_loopback_dns_or_out_of_scope_ports(self):
        for url in ('http://localhost:18083/', 'http://127.0.0.1:18083/',
                    'http://[::1]:18083/', 'http://condor.lab:18083/',
                    'http://192.168.146.137/', 'http://192.168.146.137:8080/',
                    'https://example.org:18083/'):
            with self.subTest(url=url):
                challenge = self.challenge([external_web.ASSET_PREFIX + url, 'LAB-KALI'])
                with self.assertRaises(ValueError):
                    external_web.portal_url(challenge)
        self.assertEqual(external_web.normalize_terminal_portal_url('http://192.168.146.137:18083/'),
                         'http://192.168.146.137:18083/')
