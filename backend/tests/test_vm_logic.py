from datetime import datetime
import hashlib
from http.client import HTTPConnection
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

from app.services import http_practice, vm_logic


spec = importlib.util.spec_from_file_location(
    'vm_logic_http_server',
    Path(http_practice.__file__).parents[1] / 'infrastructure/injection/scripts/linux/ctf-http-practice.py',
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


def run_record(run_id=701, user_id=8):
    return SimpleNamespace(id=run_id, user_id=user_id, challenge_id=17,
                           workspace_strategy=vm_logic.STRATEGY)


class VmLogicCaseTests(unittest.TestCase):
    def test_cases_are_reproducible_and_change_with_run_or_player(self):
        for code in vm_logic.CODES:
            with self.subTest(code=code):
                run = run_record()
                bundle, expected = vm_logic.case_for(run, code)
                self.assertEqual(vm_logic.case_for(run, code), (bundle, expected))
                self.assertEqual(bundle['code'], code)
                self.assertEqual({field['key'] for field in bundle['answer_fields']}, set(expected))
                self.assertTrue(vm_logic.matches_answer(code, expected, expected))
                self.assertNotIn('FLAG{', json.dumps(bundle))
                for changed in (run_record(702), run_record(user_id=9)):
                    changed_bundle, changed_answer = vm_logic.case_for(changed, code)
                    self.assertNotEqual(changed_bundle, bundle)
                    self.assertNotEqual(changed_answer, expected)
                    self.assertNotEqual(vm_logic.flag_for(run), vm_logic.flag_for(changed))
        with self.assertRaises(ValueError):
            vm_logic.case_for(run_record(), 'UNKNOWN')

    def test_metadata_only_contains_the_entry_point_and_answer_contract(self):
        for code in vm_logic.CODES:
            with self.subTest(code=code):
                run = run_record()
                bundle, expected = vm_logic.case_for(run, code)
                metadata = vm_logic.metadata(run, code)
                self.assertEqual(set(metadata), {'target', 'base_url', 'objective', 'answer_fields', 'note'})
                self.assertEqual(metadata['base_url'],
                                 f'http://{http_practice.HOST}:{http_practice.PORT}/practice/{run.id}/')
                self.assertEqual(metadata['answer_fields'], bundle['answer_fields'])
                serialized = json.dumps(metadata)
                for private_key in ('password_sha256', 'web_data', 'files', 'commands', 'solution', 'flag'):
                    self.assertNotIn(private_key, metadata)
                self.assertNotIn('FLAG{', serialized)
                # El destino DFIR es parte de la consigna pública; los IDs que
                # identifican la sesión correcta sí requieren correlación.
                private_answers = ({key: value for key, value in expected.items()
                                    if key not in ('destination', 'auth_utc')}
                                   if code == 'DFIR-01' else expected)
                for answer in private_answers.values():
                    self.assertNotIn(answer, serialized)
                if bundle['web_data'].get('password_sha256'):
                    self.assertNotIn(bundle['web_data']['password_sha256'], serialized)
                for entry in bundle['files'].values():
                    self.assertNotIn(entry['body'], serialized)

    def test_answers_require_all_fields_and_reject_wrong_values_or_types(self):
        for code in vm_logic.CODES:
            with self.subTest(code=code):
                _, expected = vm_logic.case_for(run_record(), code)
                key = next(iter(expected))
                self.assertFalse(vm_logic.matches_answer(code, expected, {}))
                self.assertFalse(vm_logic.matches_answer(code, expected, {**expected, 'extra': 'value'}))
                self.assertFalse(vm_logic.matches_answer(code, expected, {**expected, key: None}))
                self.assertFalse(vm_logic.matches_answer(code, expected, {**expected, key: 123}))
                self.assertFalse(vm_logic.matches_answer(code, expected, {**expected, key: 'wrong'}))
                self.assertTrue(vm_logic.matches_answer(code, expected,
                                                       {name: '  ' + value + '  ' for name, value in expected.items()}))
                if code != 'DFIR-01':
                    self.assertTrue(vm_logic.matches_answer(code, expected,
                                                           {name: value.upper() for name, value in expected.items()}))
                else:
                    self.assertTrue(vm_logic.matches_answer(code, expected,
                                                           {**expected, 'auth_utc': expected['auth_utc'].replace('+00:00', 'Z')}))
                    self.assertFalse(vm_logic.matches_answer(code, expected,
                                                            {**expected, 'auth_utc': expected['auth_utc'][:-6]}))


class VmLogicHTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.server = server.PracticeHTTPServer(('127.0.0.1', 0), self.directory.name,
                                                allowed=('127.0.0.1',))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=3)

    def publish(self, code, run_id=701, *, strategy=vm_logic.STRATEGY, expires=None):
        bundle, expected = vm_logic.case_for(run_record(run_id), code)
        record = {'strategy': strategy, 'flag': 'FLAG{test}', 'case': bundle,
                  'expires_at': time.time() + 60 if expires is None else expires}
        if strategy == server.PASSWORD_STRATEGY:
            record['password_sha256'] = hashlib.sha256(b'OnlyForLab').hexdigest()
        path = Path(self.directory.name) / f'ctf{run_id}.json'
        path.write_text(json.dumps(record), encoding='utf-8')
        return path, bundle, expected

    def request(self, path, method='GET', payload=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        body = None if payload is None else json.dumps(payload).encode('utf-8')
        headers = {} if payload is None else {'Content-Type': 'application/json'}
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def acquire(self, path):
        status, data, headers = self.request(path)
        self.assertEqual(status, 200, path)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn(b'FLAG{', data)
        return data

    def acquire_json(self, path):
        return json.loads(self.acquire(path))

    def test_web02_real_post_demonstrates_role_bypass_without_verified_password(self):
        _, _, expected = self.publish('WEB-02')
        root = '/practice/701/'
        self.assertIn(b'assets/login.js', self.acquire(root))
        client = self.acquire(root + 'assets/login.js').decode('utf-8')
        user = json.loads(re.search(r'const account = ("[^"]+");', client).group(1))
        role = json.loads(re.search(r'role === ("[^"]+")', client).group(1))
        payload = {'user': user, 'password': 'deliberately-incorrect-password', 'role': 'admin'}
        status, body, _ = self.request(root + 'login', 'POST', payload)
        self.assertEqual(status, 401)
        self.assertNotIn(b'session', body)
        payload['role'] = role
        status, body, headers = self.request(root + 'login', 'POST', payload)
        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertTrue(response['authenticated'])
        self.assertIs(response['password_verified'], False)
        observed = {'session': response['session'], 'role': response['role']}
        self.assertEqual(observed, expected)
        self.assertTrue(vm_logic.matches_answer('WEB-02', expected, observed))
        self.assertNotIn(b'FLAG{', body)
        self.assertNotIn(b'password_sha256', body)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(self.request(root + 'login', 'POST', {**payload, 'user': 'another-account'})[0], 401)
        for malformed in ({}, {**payload, 'extra': True}, {**payload, 'password': {'value': 'test'}}):
            self.assertEqual(self.request(root + 'login', 'POST', malformed)[0], 400)

    def test_web06_related_document_has_another_owner_in_the_same_case(self):
        _, _, expected = self.publish('WEB-06')
        root = '/practice/701/'
        self.assertIn(b'api/profile', self.acquire(root))
        profile = self.acquire_json(root + 'api/profile')
        listing = self.acquire_json(root + 'api/documents')
        self.assertEqual([item['id'] for item in listing['documents']], profile['document_ids'])
        own = self.acquire_json(root + f"api/documents/{profile['document_ids'][0]}")
        self.assertEqual(own['owner'], profile['user'])
        related = self.acquire_json(root + f"api/documents/{own['related_document']}")
        self.assertNotEqual(related['owner'], profile['user'])
        self.assertEqual(related['review_case'], own['review_case'])
        observed = {'object': str(related['id']), 'owner': related['owner'], 'evidence': related['evidence']}
        self.assertEqual(observed, expected)
        self.assertTrue(vm_logic.matches_answer('WEB-06', expected, observed))
        self.assertEqual(self.request(root + 'api/documents/99999999')[0], 404)
        self.assertEqual(self.request(root + 'login', 'POST', {'user': 'x', 'password': 'x', 'role': 'x'})[0], 404)

    def test_for05_acquires_and_hashes_every_artifact_to_identify_the_changed_one(self):
        _, _, expected = self.publish('FOR-05')
        root = '/practice/701/'
        self.assertIn(b'acquisition.json', self.acquire(root))
        manifest = self.acquire_json(root + 'acquisition.json')
        self.assertEqual(manifest['algorithm'], 'SHA-256')
        self.assertEqual(len(manifest['artifacts']), 8)
        changed = []
        for artifact in manifest['artifacts']:
            observed_hash = hashlib.sha256(self.acquire(root + artifact['path'])).hexdigest()
            if observed_hash != artifact['sha256_at_acquisition']:
                changed.append({'file': artifact['file'],
                                'expected_sha256': artifact['sha256_at_acquisition'],
                                'observed_sha256': observed_hash})
        self.assertEqual(changed, [expected])
        self.assertNotEqual(changed[0]['expected_sha256'], changed[0]['observed_sha256'])
        self.assertTrue(vm_logic.matches_answer('FOR-05', expected, changed[0]))

    def test_dfir_acquisition_integrity_and_independent_clock_corrected_correlation(self):
        _, _, expected = self.publish('DFIR-01')
        root = '/practice/701/'
        manifest = self.acquire_json(root + 'manifest.json')
        self.assertEqual(set(manifest['sha256']), {'auth.json', 'http.json', 'network.json', 'calibration.json'})
        sources = {}
        for name, expected_hash in manifest['sha256'].items():
            raw = self.acquire(root + name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected_hash)
            sources[name] = json.loads(raw)
        beacons = sources['calibration.json']['calibration']
        self.assertEqual(len(beacons), 2)
        auth_offsets = {datetime.fromisoformat(row['auth_clock']) - datetime.fromisoformat(row['reference_utc']) for row in beacons}
        http_offsets = {datetime.fromisoformat(row['http_clock']) - datetime.fromisoformat(row['reference_utc']) for row in beacons}
        self.assertEqual(len(auth_offsets), 1)
        self.assertEqual(len(http_offsets), 1)
        auth_offset, http_offset = next(iter(auth_offsets)), next(iter(http_offsets))
        self.assertNotEqual(auth_offset.total_seconds(), 0)
        self.assertNotEqual(http_offset.total_seconds(), 0)
        candidates = []
        for auth in sources['auth.json']:
            auth_utc = datetime.fromisoformat(auth['time']) - auth_offset
            for http in sources['http.json']:
                http_utc = datetime.fromisoformat(http['time']) - http_offset
                for network in sources['network.json']:
                    network_utc = datetime.fromisoformat(network['time'])
                    if (auth['result'] == 'success' and auth['mfa'] == 'bypassed'
                            and auth['session'] == http['session'] and http['path'] == '/reports/export'
                            and http['status'] == 200 and http['bytes'] > 500000
                            and http['request'] == network['request'] and http['bytes'] == network['bytes']
                            and network['destination'] == '203.0.113.77'
                            and 0 <= (http_utc - auth_utc).total_seconds() < 60
                            and 0 <= (network_utc - auth_utc).total_seconds() < 60):
                        candidates.append({'session': auth['session'], 'user': auth['user'],
                                           'request': http['request'], 'destination': network['destination'],
                                           'auth_utc': auth_utc.isoformat()})
        self.assertEqual(candidates, [expected])
        self.assertTrue(vm_logic.matches_answer('DFIR-01', expected, candidates[0]))
        self.assertFalse(vm_logic.matches_answer('DFIR-01', expected,
                                                {**candidates[0], 'request': 'unrelated-request'}))

    def test_expired_or_removed_records_revoke_get_and_post_access(self):
        root = '/practice/701/'
        payload = {'user': 'x', 'password': 'x', 'role': 'x'}
        for expires in (time.time() - 1, '2099', True, float('inf'), float('nan')):
            with self.subTest(expires=expires):
                self.publish('WEB-02', expires=expires)
                self.assertEqual(self.request(root)[0], 404)
                self.assertEqual(self.request(root + 'assets/login.js')[0], 404)
                self.assertEqual(self.request(root + 'login', 'POST', payload)[0], 404)
        record, _, _ = self.publish('WEB-02')
        self.assertEqual(self.request(root)[0], 200)
        record.unlink()
        self.assertEqual(self.request(root)[0], 404)
        self.assertEqual(self.request(root + 'login', 'POST', payload)[0], 404)

    def test_private_paths_aliases_and_other_strategy_endpoints_are_unavailable(self):
        self.publish('WEB-02')
        self.publish('WEB-06', run_id=702)
        self.publish('FOR-05', run_id=703)
        self.publish('DFIR-01', run_id=704)
        self.publish('WEB-02', run_id=705, strategy=server.PASSWORD_STRATEGY)
        for path in (
            '/etc/passwd', '/practice/701/../ctf702.json', '/practice/701/%2e%2e/ctf702.json',
            '/practice/701/assets/../../server.py', '/practice/701//assets/login.js',
            '/practice/0701/assets/login.js', '/practice/701/assets/login.js?file=/etc/passwd',
            '/practice/701%2fassets%2flogin.js', '/practice/701/assets\\login.js',
            '/practice/701/ctf701.json', '/practice/701/case.json', '/practice/701/private/flag.txt',
            '/practice/701/api/profile', '/practice/701/api/documents', '/practice/702/assets/login.js',
            '/practice/703/api/profile', '/practice/704/acquisition.json', '/practice/705/assets/login.js',
            '/practice/705/api/profile', '/practice/999/index.html',
        ):
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 404)
                self.assertNotIn(b'FLAG{', body)
                self.assertNotIn(b'password_sha256', body)
        payload = {'user': 'x', 'password': 'x', 'role': 'x'}
        self.assertEqual(self.request('/practice/705/login', 'POST', payload)[0], 404)
        self.assertEqual(self.request('/practice/703/login', 'POST', payload)[0], 404)
        self.assertEqual(self.request('/practice/704/manifest.json', 'DELETE')[0], 405)


if __name__ == '__main__':
    unittest.main()
