import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.services import dvwa_sql_practice as dvwa


spec = importlib.util.spec_from_file_location(
    'restricted_dvwa',
    Path(__file__).parents[1] / 'app/infrastructure/injection/scripts/linux/ctf-dvwa-flag.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class DvwaSqlTests(unittest.TestCase):
    def test_one_row_and_flag_per_run(self):
        a = SimpleNamespace(id=10, user_id=6)
        b = SimpleNamespace(id=11, user_id=6)
        self.assertEqual(dvwa.row_id(a.id), 1000010)
        self.assertNotEqual(dvwa.flag_for(a), dvwa.flag_for(b))
        self.assertIn('flag', dvwa.instructions(a)['mission'].lower())

    def test_helper_limits_mutations_to_scoped_rows(self):
        sql = helper.sql_command(['--upsert', '1000010'], 'FLAG{dvwa_sql_' + 'a'*40 + '}\n')
        self.assertIn('ctf_app_db.secrets', sql)
        self.assertIn('1000010', sql)
        self.assertIn('ON DUPLICATE KEY UPDATE', sql)
        self.assertEqual(helper.sql_command(['--delete', '1000010'], ''),
                         'DELETE FROM ctf_app_db.secrets WHERE id=1000010;')
        for row in ('1', '0', '1000000', '2147483648', '1;DELETE FROM dvwa'):
            with self.subTest(row=row), self.assertRaises(ValueError):
                helper.sql_command(['--delete', row], '')

    def test_helper_rejects_incorrect_flag(self):
        with self.assertRaises(ValueError):
            helper.sql_command(['--upsert', '1000010'], "FLAG{invalid}'")

    def test_delete_does_not_read_open_stdin(self):
        stdin = MagicMock()
        completed = SimpleNamespace(returncode=0)
        with (patch.object(helper.sys, 'argv', ['ctf-dvwa-flag', '--delete', '1000010']),
              patch.object(helper.sys, 'stdin', stdin),
              patch.object(helper.subprocess, 'run', return_value=completed)):
            self.assertEqual(helper.main(), 0)
        stdin.read.assert_not_called()
