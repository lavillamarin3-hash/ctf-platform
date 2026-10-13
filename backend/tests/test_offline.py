"""Solutores independientes: usan únicamente los archivos entregados al alumno."""
import ast
import base64
import hashlib
import io
import json
import math
import re
import struct
import unittest
import zipfile
import zlib
from app.domain.challenges.offline import CATALOG, build_case, archive, matches_answer


def solve(code, bundle):
    f = {name: base64.b64decode(data) for name, data in bundle['files'].items()}
    def js(name): return json.loads(f[name])
    kind = CATALOG[code][1]
    if kind == 'base64': return base64.b64decode(f['message.txt']).decode()
    if kind == 'http': return base64.b64decode(re.search(rb'X-Evidence-Base64: (\S+)', f['response.http'])[1]).decode()
    if kind in ('xor', 'hex_xor'):
        obj = js('cipher.json'); data = bytes.fromhex(obj['hex'])
        if kind == 'hex_xor': return bytes(b ^ obj['key'] for b in data).decode()
        solutions = [bytes(b ^ k for b in data)[4:].decode('ascii') for k in range(256) if bytes(b ^ k for b in data).startswith(b'CTF:')]
        assert len(solutions) == 1
        return solutions[0]
    if kind == 'rsa':
        obj = js('rsa.json'); n = obj['n']
        p = next(i for i in range(2, math.isqrt(n)+1) if n % i == 0)
        return str(pow(obj['c'], pow(obj['e'], -1, (p-1)*(n//p-1)), n))
    if kind in ('chunks', 'dns_chunks'):
        rows = [r for r in js('fragments.json') if r.get('domain', 'transfer.example') == 'transfer.example']
        return base64.b64decode(''.join(r['data'] for r in sorted(rows, key=lambda r:r['seq']))).decode()
    if kind == 'tree':
        target = {'003':'practice/evidence.txt', 'CTF-LNX-02':'opt/ctf/flag.txt', 'MISC-02':'var/archive/incident/evidence.txt'}[code]
        return f[target].decode().strip().split('=')[1]
    if kind == 'logs':
        rows = [r['session'] for r in js('auth.json') if r['result']=='success' and r['role']=='admin' and r['mfa']=='bypassed']
    elif kind == 'join':
        rows = [h['request'] for h in js('http.json') for n in js('network.json') if h['request']==n['request'] and h['status']==200 and h['method']=='POST' and h['path']=='/admin/export' and n['destination']=='203.0.113.77']
    elif kind == 'lateral':
        rows = [a['LogonId'] for a in js('logons.json') for s in js('services.json') if a['LogonId']==s['LogonId'] and a['LogonType']==3 and a['source']=='WS-A' and a['host']==s['host']=='WS-B' and s['service']=='update-agent']
    elif kind == 'services':
        rows = [str(r['port']) for r in js('sockets.json') if r['protocol']=='tcp' and r['state']=='LISTEN' and r['process']=='sshd']
    elif kind in ('metadata', 'stego'):
        png = f['image.png']; assert png[:8] == b'\x89PNG\r\n\x1a\n'
        position = 8; chunks = {}
        while position < len(png):
            size = struct.unpack('!I', png[position:position+4])[0]; typ = png[position+4:position+8]; data = png[position+8:position+8+size]
            assert zlib.crc32(typ+data) == struct.unpack('!I', png[position+8+size:position+12+size])[0]
            chunks[typ] = data; position += size+12
        if kind == 'metadata': return chunks[b'tEXt'].split(b'\0')[1].decode()
        width, height = struct.unpack('!2I', chunks[b'IHDR'][:8]); raw = zlib.decompress(chunks[b'IDAT'])
        pixels = b''.join(raw[y*(width*3+1)+1:(y+1)*(width*3+1)] for y in range(height))
        bits = ''.join(str(b & 1) for b in pixels)
        message = bytes(int(bits[i:i+8],2) for i in range(0,len(bits),8)).split(b'\0')[0]
        assert message.startswith(b'CTF:'); return message[4:].decode()
    elif kind in ('strings', 'memory'):
        prefix = b'ACTIVE_EVIDENCE=' if kind=='strings' else 'CASE_ACTIVE='.encode('utf-16le')
        data = f['sample.bin'].split(prefix)[1]
        if kind=='strings': return data.split(b'\0')[0].decode()
        end = next(i for i in range(0,len(data)-1,2) if data[i:i+2]==b'\0\0')
        return data[:end].decode('utf-16le')
    elif kind == 'pcap':
        capture = f['capture.pcap']; assert struct.unpack('<I', capture[:4])[0]==0xa1b2c3d4
        length = struct.unpack('<I',capture[32:36])[0]; packet = capture[40:40+length]
        assert packet[12:14]==b'\x08\x00' and packet[23]==17
        assert struct.unpack('!H',packet[36:38])[0]==9000
        return packet[42:].decode().split('=')[1]
    elif kind == 'integrity': rows = [name for name,digest in js('acquisition.json').items() if hashlib.sha256(f[name]).hexdigest()!=digest]
    elif kind == 'tutorial': return hashlib.sha256(f['evidence.txt']).hexdigest()
    elif kind == 'dns':
        zone = js('zone.json'); alias = next(r['value'] for r in zone if r['name']=='portal.training.example' and r['type']=='CNAME')
        return next(r['value'].split('=')[1] for r in zone if r['name']==alias and r['type']=='TXT')
    elif kind == 'stack':
        obj = js('stack.json'); return str(int(obj['return_address_slot'],16)-int(obj['buffer_address'],16))+':'+obj['symbols']['win']
    elif kind == 'validator':
        parsed = ast.parse(f['validator.py']); values = {node.targets[0].id:ast.literal_eval(node.value) for node in parsed.body if isinstance(node,ast.Assign)}
        return bytes((b-values['KEY'])%256 for b in values['TARGET'][::-1]).decode()
    elif kind == 'robots':
        path = re.search(rb'Disallow: /(\S+)',f['site/robots.txt'])[1].decode(); return js('site/'+path)['evidence']
    elif kind == 'auth': rows = [r['id'] for r in js('requests.json') if r['role']=='admin' and not r['password_ok']]
    elif kind == 'sql': rows = [r['request_id'] for r in js('queries.json') if 'OR 1=1 --' in r['sql']]
    elif kind == 'upload': rows = [r['id'] for r in js('uploads.json') if r['accepted'] and r['signature']!='89504e470d0a1a0a']
    elif kind == 'idor':
        owners = {r['id']:r['owner'] for r in js('objects.json')}
        rows = [r['id'] for r in js('requests.json') if r['status']==200 and r['role']!='admin' and r['user']!=owners[r['object']]]
    elif kind == 'windows': rows = [r['ComputerName'] for r in js('inventory.json') if r['OS']=='Windows' and r['DomainJoined'] and not r['BitLocker']]
    elif kind == 'process': rows = [s['name'] for s in js('services.json') for p in js('processes.json') if s['PID']==p['PID'] and s['status']=='Running' and p['path']=='C:\\Users\\Public\\update.exe']
    else: raise AssertionError('Missing independent solver')
    assert len(rows)==1, (code, rows)
    return rows[0]


class OfflineTests(unittest.TestCase):
    def test_all_exercises_solvable_from_public_files(self):
        self.assertEqual(len(CATALOG), 35)
        for code in CATALOG:
            for seed in range(20):
                with self.subTest(code=code, seed=seed):
                    public, expected = build_case(code, str(seed))
                    self.assertTrue(matches_answer(expected, solve(code, public)))
                    self.assertFalse(matches_answer(expected, 'incorrecta'))
                    self.assertNotIn('FLAG{', json.dumps(public))
                    self.assertEqual(public, build_case(code, str(seed))[0])
                    for name,data in public['files'].items():
                        self.assertEqual(hashlib.sha256(base64.b64decode(data)).hexdigest(), public['sha256'][name])

    def test_archives_and_per_run_variation(self):
        for code in CATALOG:
            public, _ = build_case(code, 'first')
            self.assertNotEqual(public, build_case(code, 'second')[0])
            with zipfile.ZipFile(io.BytesIO(archive(public))) as zipped:
                self.assertIsNone(zipped.testzip())
                self.assertIn('README.txt', zipped.namelist())
                for name,data in public['files'].items():
                    self.assertFalse(name.startswith('/') or '..' in name.split('/'))
                    self.assertEqual(zipped.read(name),base64.b64decode(data))
