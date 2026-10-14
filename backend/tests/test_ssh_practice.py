import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import tempfile
import time
from types import SimpleNamespace
import unittest
import zipfile
import paramiko
from app.services import ssh_practice, kali_workspace

spec=importlib.util.spec_from_file_location('practice_server',Path(ssh_practice.__file__).parents[1]/'infrastructure/injection/scripts/linux/ctf-ssh-practice.py')
server=importlib.util.module_from_spec(spec); spec.loader.exec_module(server)


class PracticeTests(unittest.TestCase):
    def test_password_auth_restriction_and_revocation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ctf101.json'
            record={'password_sha256':hashlib.sha256(b'OnlyForLab').hexdigest(),'flag':'FLAG{test}','expires_at':time.time()+60}
            path.write_text(json.dumps(record))
            ssh=server.PracticeServer(directory)
            self.assertEqual(ssh.check_auth_password('../ctf101','OnlyForLab'),paramiko.AUTH_FAILED)
            self.assertEqual(ssh.check_auth_password('ctf101','wrong'),paramiko.AUTH_FAILED)
            self.assertEqual(ssh.check_auth_password('ctf101','OnlyForLab'),paramiko.AUTH_SUCCESSFUL)
            self.assertEqual(ssh.execute('cat flag.txt'),'FLAG{test}\n')
            self.assertNotIn('FLAG{',ssh.execute('cat /etc/passwd'))
            self.assertNotIn('FLAG{',ssh.execute('cat flag.txt; id'))
            self.assertNotEqual(ssh.check_channel_request('direct-tcpip',0),paramiko.OPEN_SUCCEEDED)
            self.assertFalse(ssh.check_channel_subsystem_request(None,'sftp'))
            record['expires_at']=time.time()-1; path.write_text(json.dumps(record))
            self.assertNotIn('FLAG{',ssh.execute('cat flag.txt'))
            path.unlink()
            self.assertEqual(ssh.check_auth_password('ctf101','OnlyForLab'),paramiko.AUTH_FAILED)

    def test_public_instructions_do_not_reveal_flag_or_selected_password(self):
        run=SimpleNamespace(id=42,user_id=8)
        info=ssh_practice.instructions(run)
        self.assertEqual(info['username'],'ctf42')
        self.assertEqual(len(info['wordlist']),12)
        self.assertNotIn('flag',info)
        self.assertNotIn('password',info)
        self.assertIn('-t 1',info['commands'][1])
        self.assertNotEqual(ssh_practice.flag_for(run),ssh_practice.flag_for(SimpleNamespace(id=43,user_id=8)))

    def test_transfer_command_roundtrip_and_safe_paths(self):
        command=kali_workspace.transfer_command(SimpleNamespace(id=42),{'sample.bin':b'\0\xff\x01','notes.txt':'áé\n'})
        args=shlex.split(command); self.assertEqual(args[:2],['python3','-c'])
        import re
        encoded=re.search(r"b64decode\('([^']+)'\)",args[2])[1]
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as z:
            self.assertEqual(z.read('sample.bin'),b'\0\xff\x01')
            self.assertEqual(z.read('notes.txt').decode(),'áé\n')
        with self.assertRaises(ValueError): kali_workspace.transfer_command(SimpleNamespace(id=1),{'../escape':'x'})
