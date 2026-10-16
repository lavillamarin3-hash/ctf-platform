import base64
from http.client import HTTPConnection, RemoteDisconnected
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from app.services import http_practice


spec = importlib.util.spec_from_file_location('http_practice_server', Path(http_practice.__file__).parents[1] / 'infrastructure/injection/scripts/linux/ctf-http-practice.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class HTTPPracticeTests(unittest.TestCase):
    def test_daemon_stays_available_for_long_policy_then_can_expire_or_be_revoked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ctf101.json'
            path.write_text(json.dumps({'expires_at': 8200}))
            self.assertTrue(server.has_active_records(directory, at=1000))
            self.assertFalse(server.has_active_records(directory, at=8200))
            path.unlink()
            self.assertFalse(server.has_active_records(directory, at=1000))
            for invalid in ('null', '{}', 'broken JSON', '{"expires_at": true}', '{"expires_at": Infinity}'):
                path.write_text(invalid)
                self.assertFalse(server.has_active_records(directory, at=1000))
            path.unlink()
            (Path(directory) / 'ctf0.json').write_text('{"expires_at":8200}')
            self.assertFalse(server.has_active_records(directory, at=1000))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.server = server.PracticeHTTPServer(('127.0.0.1', 0), self.directory.name, allowed=('127.0.0.1',))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=3)

    def record(self, run_id, strategy, expires=None):
        data = {'strategy': strategy, 'flag': f'FLAG{{test_{run_id}}}',
                'expires_at': expires if expires is not None else time.time() + 60}
        if strategy == server.PASSWORD_STRATEGY:
            data['password_sha256'] = hashlib.sha256(b'OnlyForLab').hexdigest()
        elif strategy == server.FILES_STRATEGY:
            data['case'] = http_practice.case_for(SimpleNamespace(id=run_id, user_id=8,
                workspace_strategy=http_practice.FILES_STRATEGY))[0]
        path = Path(self.directory.name) / f'ctf{run_id}.json'
        path.write_text(json.dumps(data))
        return path

    def request(self, path, credentials=None, method='GET', headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        request_headers = dict(headers or {})
        if credentials is not None:
            request_headers['Authorization'] = 'Basic ' + base64.b64encode(credentials.encode()).decode()
        try:
            connection.request(method, path, headers=request_headers)
            response = connection.getresponse()
            return response.status, response.read().decode(), dict(response.getheaders())
        finally:
            connection.close()

    def test_web_password_auth_real_http_and_revocation(self):
        path = self.record(101, server.PASSWORD_STRATEGY)
        route = '/practice/101/private/flag.txt'
        status, body, headers = self.request(route)
        self.assertEqual(status, 401)
        self.assertIn('Basic', headers['WWW-Authenticate'])
        self.assertNotIn('FLAG{', body)
        self.assertEqual(self.request(route, 'ctf101:wrong')[0], 401)
        self.assertEqual(self.request(route, 'ctf102:OnlyForLab')[0], 401)
        self.assertEqual(self.request(route, 'cuentañ:OnlyForLab')[0], 401)
        self.assertEqual(self.request(route, headers={'Authorization': 'Basic !!!!'})[0], 401)
        status, body, headers = self.request(route, 'ctf101:OnlyForLab')
        self.assertEqual((status, body), (200, 'FLAG{test_101}\n'))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('OnlyForLab', body)
        path.unlink()
        self.assertEqual(self.request(route, 'ctf101:OnlyForLab')[0], 404)
        self.record(101, server.PASSWORD_STRATEGY, time.time() - 1)
        self.assertEqual(self.request(route, 'ctf101:OnlyForLab')[0], 404)

    def test_exposed_file_discovery_is_confined_to_own_run(self):
        self.record(202, server.FILES_STRATEGY)
        status, body, _ = self.request('/practice/202/robots.txt')
        self.assertEqual(status, 200)
        directory = re.search(r'Disallow: (\S+)', body).group(1)
        self.assertRegex(directory, r'^/practice/202/archive-[0-9a-f]{8}/$')
        self.assertNotIn('FLAG{', body)
        status, body, _ = self.request(directory)
        self.assertEqual(status, 200)
        self.assertNotIn('FLAG{', body)
        names = re.findall(r'href="(backup-[a-f0-9]+\.json)"', body)
        self.assertEqual(len(names), 3)
        manifest = json.loads(self.request(directory + 'manifest.json')[1])
        matching = []
        for name in names:
            status, raw, _ = self.request(directory + name)
            self.assertEqual(status, 200)
            self.assertNotIn('FLAG{', raw)
            document = json.loads(raw)
            if document['release'] == manifest['current_release'] and hashlib.sha256(raw.encode()).hexdigest() == manifest['sha256']:
                encoded = bytes.fromhex(''.join(row['hex'] for row in sorted(document['fragments'], key=lambda row: row['seq'])))
                matching.append({'backup': name, 'release': document['release'],
                                 'evidence': bytes(value ^ manifest['key'] for value in encoded).decode()})
        self.assertEqual(len(matching), 1)
        _, expected = http_practice.case_for(SimpleNamespace(id=202, user_id=8, workspace_strategy=http_practice.FILES_STRATEGY))
        self.assertEqual(matching[0], expected)
        self.assertEqual(self.request(directory.replace('/202/', '/203/') + names[0])[0], 404)
        self.assertEqual(self.request('/practice/202/private/flag.txt', 'ctf202:OnlyForLab')[0], 404)
        self.record(101, server.PASSWORD_STRATEGY)
        self.assertEqual(self.request('/practice/101/robots.txt')[0], 404)

    def test_traversal_aliases_and_unsupported_methods_rejected(self):
        self.record(101, server.PASSWORD_STRATEGY)
        self.record(202, server.FILES_STRATEGY)
        for route in ['/etc/passwd', '/practice/202/../ctf101.json', '/practice/202/backup/../../server.py',
                      '/practice/202/backup/%2e%2e/%2e%2e/ctf101.json',
                      '/practice/202%2fbackup%2faudit-backup.txt', '/practice/202/backup/%252e%252e/server.py',
                      '/practice/0202/robots.txt', '/practice/202/robots.txt?file=/etc/passwd',
                      '/practice/202/backup/missing.txt', '/practice/202\\backup/audit-backup.txt']:
            with self.subTest(route=route):
                status, body, _ = self.request(route)
                self.assertEqual(status, 404)
                self.assertNotIn('FLAG{', body)
        self.assertEqual(self.request('/practice/202/robots.txt', method='POST')[0], 405)

    def test_invalid_expiration_and_denied_source(self):
        path = self.record(202, server.FILES_STRATEGY)
        for expires in ['2099', True, float('inf'), float('nan')]:
            data = {'strategy': server.FILES_STRATEGY, 'flag': 'FLAG{invalid}', 'expires_at': expires}
            path.write_text(json.dumps(data))
            self.assertEqual(self.request('/practice/202/robots.txt')[0], 404)
        self.server.allowed = frozenset(('192.0.2.1',))
        with self.assertRaises((RemoteDisconnected, ConnectionResetError)):
            self.request('/practice/202/robots.txt')

    def test_public_instructions_and_dynamic_secrets(self):
        run = SimpleNamespace(id=42, user_id=8, workspace_strategy=http_practice.PASSWORD_STRATEGY)
        info = http_practice.instructions(run)
        self.assertEqual(info['username'], 'ctf42')
        self.assertIsInstance(info['objective'], str)
        self.assertEqual(len(info['wordlist']), 12)
        self.assertNotIn('flag', info)
        self.assertNotIn('password', info)
        self.assertEqual(info['commands'], [])
        self.assertIn('private/flag.txt', info['note'])
        other_run = SimpleNamespace(id=43, user_id=8, workspace_strategy=http_practice.PASSWORD_STRATEGY)
        self.assertNotEqual(http_practice.flag_for(run), http_practice.flag_for(other_run))
        files_run = SimpleNamespace(id=42, user_id=8, workspace_strategy=http_practice.FILES_STRATEGY)
        self.assertNotEqual(http_practice.flag_for(run), http_practice.flag_for(files_run))
        self.assertNotIn('username', http_practice.instructions(files_run))
        self.assertNotIn('wordlist', http_practice.instructions(files_run))
        self.assertEqual(http_practice.instructions(files_run)['commands'], [])
        self.assertEqual({field['key'] for field in http_practice.instructions(files_run)['answer_fields']}, {'backup', 'release', 'evidence'})
        with self.assertRaises(ValueError):
            http_practice.instructions(SimpleNamespace(id=42, workspace_strategy='offline_case'))


if __name__ == '__main__':
    unittest.main()
