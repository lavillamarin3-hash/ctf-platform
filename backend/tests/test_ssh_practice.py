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
from unittest.mock import MagicMock, patch
import zipfile
import paramiko
from app.services import ssh_practice, kali_workspace

spec=importlib.util.spec_from_file_location('practice_server',Path(ssh_practice.__file__).parents[1]/'infrastructure/injection/scripts/linux/ctf-ssh-practice.py')
server=importlib.util.module_from_spec(spec); spec.loader.exec_module(server)


class PracticeTests(unittest.TestCase):
    def test_daemon_lifetime_follows_real_record_expiry_and_revocation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            valid = folder / 'ctf101.json'
            valid.write_text(json.dumps({'expires_at': 8200}))
            self.assertTrue(server.has_active_records(directory, at=1000))
            self.assertFalse(server.has_active_records(directory, at=8200))
            valid.unlink()
            self.assertFalse(server.has_active_records(directory, at=1000))
            for invalid in ('null', '{}', 'broken JSON', '{"expires_at": true}', '{"expires_at": NaN}'):
                valid.write_text(invalid)
                self.assertFalse(server.has_active_records(directory, at=1000))
            valid.unlink()
            (folder / 'ctf0.json').write_text('{"expires_at": 8200}')
            (folder / 'other.json').write_text('{"expires_at": 8200}')
            self.assertFalse(server.has_active_records(directory, at=1000))

    def test_provision_upgrades_only_own_daemon_preserves_records_and_retries_readiness(self):
        source = Path(ssh_practice.__file__).parents[1].joinpath(
            'infrastructure/injection/scripts/linux/ctf-ssh-practice.py').read_bytes()
        directory = '/home/lab/.ctf-ssh-practice'
        for old_source in (None, source, b'# previous practice daemon'):
            with self.subTest(upgrade=old_source != source and old_source is not None):
                files = {directory + '/ctf9.json': b'{"expires_at":9999999999}',
                         directory + '/host-key': b'preserved host key'}
                if old_source is not None:
                    files[directory + '/server.py'] = old_source
                sftp = MagicMock()
                sftp.__enter__.return_value = sftp
                sftp.normalize.return_value = '/home/lab'

                class RemoteFile(io.BytesIO):
                    def __init__(self, path, mode):
                        self.path, self.mode = path, mode
                        super().__init__(files.get(path, b''))

                    def write(self, data):
                        return super().write(data.encode() if isinstance(data, str) else data)

                    def close(self):
                        if not self.closed and self.mode == 'w':
                            files[self.path] = self.getvalue()
                        super().close()

                def remote_open(path, mode):
                    if mode == 'rb' and path not in files:
                        raise FileNotFoundError(path)
                    return RemoteFile(path, mode)

                def rename(old, new):
                    files[new] = files.pop(old)

                sftp.open.side_effect = remote_open
                sftp.posix_rename.side_effect = rename
                client = MagicMock()
                client.open_sftp.return_value = sftp
                channel = MagicMock()
                client.get_transport.return_value.open_channel.side_effect = [OSError(), OSError(), channel]
                context = MagicMock()
                context.__enter__.return_value = client
                with patch.object(ssh_practice, 'connection', return_value=context), \
                     patch.object(ssh_practice, '_command') as command, \
                     patch.object(ssh_practice.time, 'sleep') as pause:
                    ssh_practice.provision(101, 'ctf101', 'OnlyForLab', 'FLAG{fixture}', 8200)
                self.assertEqual(files[directory + '/server.py'], source)
                self.assertEqual(files[directory + '/host-key'], b'preserved host key')
                self.assertEqual(files[directory + '/ctf9.json'], b'{"expires_at":9999999999}')
                config = json.loads(files[directory + '/ctf101.json'])
                self.assertEqual(config['expires_at'], 8200)
                self.assertEqual(config['password_sha256'], hashlib.sha256(b'OnlyForLab').hexdigest())
                self.assertNotIn('OnlyForLab', json.dumps(config))
                self.assertEqual(pause.call_count, 2)
                channel.close.assert_called_once()
                sftp.remove.assert_not_called()
                self.assertEqual(sftp.posix_rename.call_count, 2)
                commands = [call.args[1] for call in command.call_args_list]
                self.assertTrue(commands[-1].startswith('nohup flock -n '))
                self.assertNotIn('OnlyForLab', '\n'.join(commands))
                self.assertNotIn('FLAG{fixture}', '\n'.join(commands))
                upgrade = old_source is not None and old_source != source
                self.assertEqual(len(commands), 2 if upgrade else 1)
                if upgrade:
                    script = shlex.split(commands[0])[2]
                    compile(script, '<safe daemon upgrade>', 'exec')
                    self.assertIn('p.stat().st_uid==os.getuid()', script)
                    self.assertIn("split(b'\\0')==expected", script)
                    self.assertIn(repr((directory + '/server.py').encode()), script)
                    self.assertIn('signal.SIGTERM', script)
                    self.assertNotIn('pkill', script)

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
