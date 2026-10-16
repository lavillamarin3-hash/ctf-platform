from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import paramiko
import configure_rdp_autoaccess as script


class RdpTargetTests(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_filter_deduplication_and_credentials_stay_private(self):
        records = {
            'rdp-a': ('rdp', '192.168.146.134'), 'rdp-b': ('rdp', '192.168.146.137'),
            'rdp-duplicate': ('rdp', '192.168.146.134'), 'rdp-other': ('rdp', '192.168.146.135'),
            'ssh': ('ssh', '192.168.146.134'),
        }
        async def request(method, path):
            self.assertEqual(method, 'GET')
            if path == '/connections':
                return {key: {'protocol': value[0]} for key, value in records.items()}
            identifier = path.split('/')[2]
            protocol, host = records[identifier]
            if path.endswith('/parameters'):
                return {'hostname': host, 'username': 'rdp-fixture', 'password': 'private-fixture-password'}
            return {'protocol': protocol, 'attributes': {}}
        admin = SimpleNamespace(_api_request=AsyncMock(side_effect=request))
        targets = await script.discover_targets(admin)
        self.assertEqual({value['host'] for value in targets}, script.LAB_HOSTS)
        self.assertEqual(len(targets), 2)
        self.assertTrue(all(value['username'] == 'rdp-fixture' for value in targets))
        with patch.object(script, 'configure_target', side_effect=lambda target, apply=False: {'host': target['host'], 'sessions': []}):
            public = await script.configure(admin)
        self.assertNotIn('private-fixture-password', json.dumps(public))
        self.assertTrue(all(call.args[0] == 'GET' for call in admin._api_request.await_args_list))
        self.assertFalse(any('/ssh' in call.args[1] for call in admin._api_request.await_args_list))


class RdpConnectionTests(unittest.TestCase):
    def test_uses_rdp_identity_and_existing_injector_host_key_policy(self):
        target = {'host': '192.168.146.134', 'username': 'rdp-fixture', 'password': 'private-fixture-password'}
        for strict, known in ((True, '/fixture/known_hosts'), (False, None)):
            with self.subTest(strict=strict):
                client = MagicMock()
                settings = SimpleNamespace(flag_injector_known_hosts=known, flag_injector_strict_host_key=strict,
                                           flag_injector_ssh_port=22)
                with patch.object(script, 'get_settings', return_value=settings), patch.object(script.paramiko, 'SSHClient', return_value=client):
                    with script.connection(target):
                        pass
                self.assertIsInstance(client.set_missing_host_key_policy.call_args.args[0],
                                      paramiko.RejectPolicy if strict else paramiko.AutoAddPolicy)
                if known:
                    client.load_host_keys.assert_called_once_with(known)
                else:
                    client.load_system_host_keys.assert_called_once_with()
                client.connect.assert_called_once_with(hostname=target['host'], port=22, username=target['username'],
                                                       password=target['password'], timeout=8, banner_timeout=8,
                                                       auth_timeout=8, allow_agent=False, look_for_keys=False)
                client.close.assert_called_once_with()

    def test_remote_invocation_has_no_credentials_and_output_is_whitelisted(self):
        target = {'host': '192.168.146.134', 'username': 'rdp-fixture', 'password': 'private-fixture-password'}
        keys = ['xfce4-screensaver:/lock/enabled', 'xfce4-screensaver:/lock/sleep-activation',
                'xfce4-screensaver:/saver/idle-activation/enabled',
                'xfce4-power-manager:/xfce4-power-manager/lock-screen-suspend-hibernate']
        values = dict.fromkeys(keys, False)
        response = {'sessions': [{'before': values, 'after': values}], 'password': target['password']}
        stdout = MagicMock()
        stdout.read.return_value = json.dumps(response).encode()
        stdout.channel.recv_exit_status.return_value = 0
        client = MagicMock()
        client.exec_command.return_value = (None, stdout, MagicMock())
        @contextmanager
        def connection(_target):
            yield client
        with patch.object(script, 'connection', connection):
            result = script.configure_target(target, apply=True)
        command = client.exec_command.call_args.args[0]
        self.assertTrue(command.endswith(' --apply'))
        self.assertNotIn(target['password'], command)
        self.assertNotIn('sudo', command)
        self.assertNotIn(target['password'], json.dumps(result))
        self.assertEqual(set(result), {'host', 'sessions'})

    def test_no_session_returns_clear_error_without_stderr(self):
        stdout = MagicMock()
        stdout.read.return_value = b'{"error":"no-session"}'
        stdout.channel.recv_exit_status.return_value = 1
        client = MagicMock()
        client.exec_command.return_value = (None, stdout, MagicMock())
        @contextmanager
        def connection(_target):
            yield client
        with patch.object(script, 'connection', connection), self.assertRaisesRegex(script.AutoAccessError, 'No hay una sesión XFCE'):
            script.configure_target({'host': '192.168.146.134'})


class XfcePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.remote = {'__name__': 'remote_test'}
        exec(script.REMOTE_SCRIPT, self.remote)

    def test_discovers_only_own_xfce_and_deduplicates_session_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            for pid, name, bus in [('101', 'xfce4-session', 'unix:path=/fixture/one'),
                                   ('102', 'xfce4-session', 'unix:path=/fixture/one'),
                                   ('103', 'xfce4-session', 'unix:path=/fixture/two'),
                                   ('104', 'bash', 'unix:path=/fixture/ignored'),
                                   ('105', 'xfce4-session', 'unix:path=/fixture/foreign-user')]:
                process = Path(directory) / pid
                process.mkdir()
                process.joinpath('comm').write_text(name)
                process.joinpath('environ').write_bytes(('DISPLAY=:10\0DBUS_SESSION_BUS_ADDRESS=' + bus
                                                        + '\0PASSWORD=private-fixture-password\0').encode())
            original_stat = Path.stat
            own_uid = Path(directory).stat().st_uid
            def stat(path, *args, **kwargs):
                if path.name == '105':
                    return SimpleNamespace(st_uid=own_uid + 1)
                return original_stat(path, *args, **kwargs)
            with patch.object(Path, 'stat', stat), patch.object(self.remote['os'], 'geteuid', return_value=own_uid, create=True):
                sessions = self.remote['discover_sessions'](directory)
        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(set(value) == {'DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'} for value in sessions))
        self.assertNotIn('private-fixture-password', json.dumps(sessions))

    def test_check_is_read_only_and_apply_creates_only_four_booleans_idempotently(self):
        preferences = self.remote['PREFERENCES']
        self.assertEqual(len(preferences), 4)
        buses = ('unix:path=/fixture/bus', 'unix:path=/fixture/second')
        values = {bus: {preferences[-1]: True} for bus in buses}
        calls = []
        environments = [{'DISPLAY': ':10', 'DBUS_SESSION_BUS_ADDRESS': buses[0]},
                        {'DISPLAY': ':11', 'DBUS_SESSION_BUS_ADDRESS': buses[1]}]
        expected_display = {environment['DBUS_SESSION_BUS_ADDRESS']: environment['DISPLAY']
                            for environment in environments}
        def run(command, **kwargs):
            bus = kwargs['env']['DBUS_SESSION_BUS_ADDRESS']
            self.assertIn(bus, buses)
            calls.append((bus, list(command)))
            self.assertEqual(kwargs['env']['DISPLAY'], expected_display[bus])
            self.assertEqual(kwargs['env']['LC_ALL'], 'C')
            key = (command[2], command[4])
            self.assertIn(key, preferences)
            session_values = values[bus]
            if '-s' in command:
                self.assertEqual(command[command.index('-s') + 1], 'false')
                if key not in session_values:
                    self.assertIn('-n', command)
                    self.assertEqual(command[command.index('-t') + 1], 'bool')
                else:
                    self.assertNotIn('-n', command)
                session_values[key] = False
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            if key not in session_values:
                return SimpleNamespace(returncode=1, stdout='', stderr='Property does not exist')
            return SimpleNamespace(returncode=0, stdout=str(session_values[key]).lower(), stderr='')
        self.remote['discover_sessions'] = lambda proc_root: environments
        with patch.object(self.remote['subprocess'], 'run', side_effect=run):
            checked = self.remote['configure'](apply=False)
            self.assertEqual(len(checked['sessions']), 2)
            self.assertEqual({bus for bus, command in calls}, set(buses))
            self.assertTrue(all('-s' not in command for bus, command in calls))
            calls.clear()
            applied = self.remote['configure'](apply=True)
            self.assertEqual(sum('-s' in command for bus, command in calls), 8)
            for expected_bus in buses:
                self.assertEqual(sum('-s' in command for bus, command in calls if bus == expected_bus), 4)
            self.assertTrue(all(value is False for session_values in values.values() for value in session_values.values()))
            self.assertTrue(all(value is False for session in applied['sessions'] for value in session['after'].values()))
            calls.clear()
            self.remote['configure'](apply=True)
            self.assertEqual({bus for bus, command in calls}, set(buses))
            self.assertTrue(all('-s' not in command for bus, command in calls))

    def test_without_live_session_never_queries_or_writes(self):
        self.remote['discover_sessions'] = lambda proc_root: []
        with patch.object(self.remote['subprocess'], 'run') as run, self.assertRaisesRegex(self.remote['PreferenceError'], 'no-session'):
            self.remote['configure'](apply=True)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
