"""Regresión: los servicios del laboratorio deben escuchar en Nutanix VLAN30.

No abre puertos ni inicia corridas ni revela flags.
"""
import importlib.util
import inspect
from pathlib import Path
import unittest

from app.services import http_practice, ssh_practice

SCRIPTS = Path(__file__).resolve().parents[1] / "app/infrastructure/injection/scripts/linux"
VICTIM = "10.10.30.12"
ATTACKERS = {"10.10.20.10", "10.10.20.11", "10.10.20.12"}


def module(filename: str):
    spec = importlib.util.spec_from_file_location(
        "ctf_lab_test_" + filename.replace(".", "_").replace("-", "_"),
        SCRIPTS / filename,
    )
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


class NutanixServiceAddressTests(unittest.TestCase):
    def test_ssh_practice_defaults_to_victim_and_kali_only(self):
        service = module("ctf-ssh-practice.py")
        signature = inspect.signature(service.serve)
        self.assertEqual(signature.parameters["bind"].default, VICTIM)
        self.assertEqual(signature.parameters["port"].default, 2222)
        self.assertEqual(set(signature.parameters["allowed"].default), ATTACKERS)
        self.assertEqual(ssh_practice.HOST, VICTIM)

    def test_http_practice_defaults_to_victim_and_kali_only(self):
        service = module("ctf-http-practice.py")
        signature = inspect.signature(service.serve)
        self.assertEqual(signature.parameters["bind"].default, VICTIM)
        self.assertEqual(set(signature.parameters["allowed"].default), ATTACKERS)
        self.assertEqual(set(inspect.signature(service.PracticeHTTPServer).parameters["allowed"].default),
                         ATTACKERS)
        self.assertEqual(http_practice.HOST, VICTIM)

    def test_evidence_endpoint_only_allows_attack_vlan(self):
        script = (SCRIPTS / "ctf-evidence-service.py").read_text(encoding="utf-8")
        service = module("ctf-evidence-service.py")
        self.assertEqual(service.EvidenceHandler.allowed_client_ips, ATTACKERS)
        self.assertIn('("10.10.30.12", 18081)', script)

    def test_no_legacy_addresses_in_dynamic_services(self):
        filenames = ("ctf-ssh-practice.py", "ctf-http-practice.py",
                     "ctf-evidence-service.py")
        for filename in filenames:
            with self.subTest(filename=filename):
                text = (SCRIPTS / filename).read_text(encoding="utf-8")
                self.assertNotIn("192.168.146.", text)


if __name__ == "__main__":
    unittest.main()
