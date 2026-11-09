import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects.postgresql import dialect
from ctf.domain.laboratory import *
from ctf.application.runs import RunService
from ctf.adapters.persistence.models import Base, Run
from ctf.adapters.http.schemas import NewUser, ChallengeInput
from ctf.adapters.injectors import SshInjector


class DomainTests(unittest.TestCase):
    def test_flags_are_random_and_run_owned(self):
        a, b = new_flag("SSH-PASSWORD-LAB"), new_flag("SSH-PASSWORD-LAB")
        self.assertNotEqual(a, b)
        self.assertTrue(verify_flag(a, flag_hash(a)))
        self.assertFalse(verify_flag(a, flag_hash(b)))
        self.assertRegex(a, r"^FLAG\{ssh_[a-f0-9]{40}\}$")

    def test_run_ids_reject_shell_arguments(self):
        for value in ("1", "A" * 12, "a123456789ab;id", "../etc/passwd", "a" * 13):
            with self.assertRaises(DomainError): validate_run_id(value)

    def test_windows_contract_disabled_and_correct_targets(self):
        scenario = scenario_for("LATERAL-SMB-LAB")
        self.assertFalse(scenario.enabled)
        self.assertEqual(scenario.victims, ("LAB-WINVICT-A", "LAB-WINVICT-B"))

    def test_pending_scenarios_cannot_be_enabled_by_environment(self):
        from ctf.adapters.http.routes import enabled
        runtime = SimpleNamespace(settings=SimpleNamespace(ssh_injector_enabled=True, dvwa_lab_enabled=True, winrm_injector_enabled=True))
        for strategy in ("RECON-SCAN-LAB", "LATERAL-SMB-LAB", "EXFIL-SMB-LAB"):
            self.assertFalse(enabled(runtime, scenario_for(strategy)))

    def test_fresh_template_matches_settings_and_compose_fields(self):
        from ctf.infrastructure.settings import Settings
        root = Path(__file__).resolve().parents[2]
        lines = (root / 'deploy/fresh.env.example').read_text(encoding='utf-8').splitlines()
        keys = {line.split('=', 1)[0] for line in lines if line and not line.startswith('#') and '=' in line}
        self.assertEqual(keys, {name.upper() for name in Settings.model_fields} | {'WEB_BIND_IP', 'WEB_PORT'})

    def test_no_web_admin_creation(self):
        with self.assertRaises(ValueError): NewUser(username="another_admin", password="random-test-password", role=1)

    def test_hint_limit(self):
        with self.assertRaises(DomainError): validate_hints([{"text": "hint"}] * 4)

    def test_physical_names_and_unique_locks(self):
        prefixes = set()
        for table in Base.metadata.tables.values():
            self.assertEqual(table.name, table.name.upper())
            table_prefixes = {column.name.split('_')[0] for column in table.columns}
            self.assertEqual(len(table_prefixes), 1)
            prefix = table_prefixes.pop()
            self.assertEqual(len(prefix), 3)
            self.assertNotIn(prefix, prefixes)
            prefixes.add(prefix)
            str(CreateTable(table).compile(dialect=dialect()))
        indexes = {index.name: str(CreateIndex(index).compile(dialect=dialect())) for index in Run.__table__.indexes}
        for name in ("uq_cor_reto_vivo", "uq_cor_atacante_vivo", "uq_cor_victima_viva"):
            self.assertIn("UNIQUE", indexes[name])
            self.assertIn("reiniciando", indexes[name])


class ProvisionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.run = SimpleNamespace(id="123456789abc", state=State.RESERVED, pilot=False, user_id="u")
        self.challenge = SimpleNamespace(strategy="SSH-PASSWORD-LAB")
        self.context = (self.run, self.challenge, SimpleNamespace(ip="10.10.30.12"), SimpleNamespace(ip="10.10.20.12"))
        self.repo = SimpleNamespace(context=AsyncMock(return_value=self.context), activate=AsyncMock(), cleaning=AsyncMock(), error=AsyncMock(), released=AsyncMock())
        self.created_flag = ""
        async def execute(host, script, action, run_id, data=""):
            if action == "create" and script.endswith("ctf-ssh-lab"): self.created_flag = data
            if action == "check": return {"flag_hash": flag_hash(self.created_flag)}
            return {}
        self.injector = SimpleNamespace(execute=AsyncMock(side_effect=execute), verify_session=AsyncMock())
        self.terminal = SimpleNamespace(create=AsyncMock(return_value="personal"), destroy=AsyncMock())
        self.cache = SimpleNamespace(lock=AsyncMock(), unlock=AsyncMock())
        self.service = RunService(self.repo, self.injector, self.terminal, self.cache)

    async def test_activates_only_after_verified_injection_and_terminal(self):
        await self.service.provision(self.run.id)
        self.repo.activate.assert_awaited_once_with(self.run.id, flag_hash(self.created_flag), "personal")
        self.assertNotIn(self.created_flag, repr(self.repo.activate.call_args))

    async def test_failure_after_create_compensates_both_vms_and_guacamole(self):
        self.terminal.create.side_effect = RuntimeError("provider secret")
        with self.assertRaises(RecursoNoDisponibleError): await self.service.provision(self.run.id)
        self.repo.activate.assert_not_awaited()
        self.repo.cleaning.assert_awaited()
        self.terminal.destroy.assert_awaited_once()
        destroyed = [c.args[1] for c in self.injector.execute.call_args_list if c.args[2] == "destroy"]
        self.assertCountEqual(destroyed, ["/usr/local/sbin/ctf-ssh-lab", "/usr/local/sbin/ctf-kali-session"])

    async def test_failed_cleanup_never_releases_resources(self):
        self.terminal.destroy.side_effect = RuntimeError()
        with self.assertRaises(RecursoNoDisponibleError): await self.service.cleanup(self.run.id)
        self.repo.released.assert_not_awaited()
        self.cache.unlock.assert_not_awaited()

    async def test_wrong_hash_never_activates(self):
        self.injector.execute.side_effect = AsyncMock(return_value={"flag_hash": "wrong"})
        with self.assertRaises(RecursoNoDisponibleError): await self.service.provision(self.run.id)
        self.repo.activate.assert_not_awaited()

    async def test_kali_login_failure_compensates_before_guacamole(self):
        self.injector.verify_session.side_effect = RecursoNoDisponibleError()
        with self.assertRaises(RecursoNoDisponibleError): await self.service.provision(self.run.id)
        self.terminal.create.assert_not_awaited()
        self.repo.activate.assert_not_awaited()

    async def test_injector_rejects_unlisted_host_and_disabled_configuration(self):
        settings = SimpleNamespace(ssh_injector_enabled=False)
        injector = SshInjector(settings)
        with self.assertRaises(RecursoNoDisponibleError):
            await injector.execute("10.195.20.11", "/usr/local/sbin/ctf-ssh-lab", "create", self.run.id)
        with self.assertRaises(RecursoNoDisponibleError):
            await injector.execute("10.10.30.12", "/usr/local/sbin/ctf-ssh-lab", "create", self.run.id)


if __name__ == "__main__": unittest.main()
