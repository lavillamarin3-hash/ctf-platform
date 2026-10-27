"""Aceptación sobre Kali/víctima reales con rollback SQL y limpieza remota.

No imprime evidencias, soluciones, contraseñas ni parámetros Guacamole.
Ejecutar después de desplegar el código, con los cuatro retos sin corridas
activas que impidan ensayar el catálogo.
"""
import asyncio
import base64
from datetime import datetime, timedelta
import hashlib
import json
import re
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urljoin, urlsplit

import paramiko
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import runs, terminal, vm_logic as vm_logic_api
from app.core import now_utc
from app.db import make_session_factory
from app.guacamole import make_guacamole_admin
from app.models import Challenge, ChallengeFlag, ChallengeGroupAssignment, ChallengeRun, GroupMembership, StudentGroup, User
from app.schemas import SubmissionRequest
from app.services import vm_logic
from app.services.vm_logic_catalog import configure


def http(client, url, data=None):
    """La petición nace en Kali; la salida queda en memoria del test."""
    script = ('import base64,json,urllib.request,urllib.error\n'
              f'url={url!r}\npayload={data!r}\n'
              'raw=None if payload is None else json.dumps(payload).encode()\n'
              'request=urllib.request.Request(url,data=raw,headers={} if raw is None else {"Content-Type":"application/json"})\n'
              'try:\n response=urllib.request.urlopen(request,timeout=15)\n'
              'except urllib.error.HTTPError as error:\n response=error\n'
              'print(json.dumps({"status":response.status,"body":base64.b64encode(response.read()).decode()}))\n')
    inp, out, err = client.exec_command('python3 -', timeout=30)
    inp.write(script)
    inp.flush()
    inp.channel.shutdown_write()
    output = out.read()
    status = out.channel.recv_exit_status()
    if status:
        err.read()
        raise AssertionError('Falló la adquisición HTTP desde Kali; salida omitida')
    result = json.loads(output)
    result['body'] = base64.b64decode(result['body'])
    return result


def get(client, base, resource):
    result = http(client, urljoin(base, resource))
    assert result['status'] == 200, 'Recurso público esperado no disponible'
    return result['body']


def solve(client, base, code):
    page = get(client, base, '').decode()
    assert 'FLAG{' not in page
    if code == 'WEB-02':
        source = get(client, base, 'assets/login.js').decode()
        account = json.loads(re.search(r'const account = ("[^"]+");', source).group(1))
        role = json.loads(re.search(r'role === ("[^"]+")', source).group(1))
        denied = http(client, urljoin(base, 'login'), {'user': account, 'password': 'intentionally-wrong', 'role': 'reader'})
        assert denied['status'] == 401
        result = http(client, urljoin(base, 'login'), {'user': account, 'password': 'intentionally-wrong', 'role': role})
        assert result['status'] == 200
        login = json.loads(result['body'])
        assert login['authenticated'] and not login['password_verified']
        return {'session': login['session'], 'role': login['role']}
    if code == 'WEB-06':
        profile = json.loads(get(client, base, 'api/profile'))
        listing = json.loads(get(client, base, 'api/documents'))
        own = listing['documents'][0]
        assert own['owner'] == profile['user']
        document = json.loads(get(client, base, 'api/documents/' + str(own['related_document'])))
        assert document['owner'] != profile['user'] and document['review_case'] == own['review_case']
        return {'object': str(document['id']), 'owner': document['owner'], 'evidence': document['evidence']}
    if code == 'FOR-05':
        manifest = json.loads(get(client, base, 'acquisition.json'))
        mismatches = []
        assert len(manifest['artifacts']) == 8
        for item in manifest['artifacts']:
            body = get(client, base, item['path'])
            digest = hashlib.sha256(body).hexdigest()
            if digest != item['sha256_at_acquisition']:
                mismatches.append({'file': item['file'], 'expected_sha256': item['sha256_at_acquisition'], 'observed_sha256': digest})
        assert len(mismatches) == 1
        return mismatches[0]
    manifest = json.loads(get(client, base, 'manifest.json'))
    sources = {}
    for name, digest in manifest['sha256'].items():
        body = get(client, base, name)
        assert hashlib.sha256(body).hexdigest() == digest
        sources[name] = json.loads(body)
    calibration = sources['calibration.json']['calibration']
    auth_offsets = {datetime.fromisoformat(row['auth_clock']) - datetime.fromisoformat(row['reference_utc']) for row in calibration}
    http_offsets = {datetime.fromisoformat(row['http_clock']) - datetime.fromisoformat(row['reference_utc']) for row in calibration}
    assert len(auth_offsets) == len(http_offsets) == 1
    auth_offset, http_offset = auth_offsets.pop(), http_offsets.pop()
    answers = []
    for auth in sources['auth.json']:
        if auth['result'] != 'success' or auth['mfa'] != 'bypassed':
            continue
        auth_utc = datetime.fromisoformat(auth['time']) - auth_offset
        for request in sources['http.json']:
            if (request['session'] != auth['session'] or request['path'] != '/reports/export'
                    or request['status'] != 200 or request['bytes'] <= 500000):
                continue
            http_utc = datetime.fromisoformat(request['time']) - http_offset
            if not 0 <= (http_utc - auth_utc).total_seconds() < 60:
                continue
            for network in sources['network.json']:
                if (network['request'] == request['request'] and network['destination'] == '203.0.113.77'
                        and 0 <= (datetime.fromisoformat(network['time']) - auth_utc).total_seconds() < 60):
                    answers.append({'session': auth['session'], 'user': auth['user'], 'request': request['request'],
                                    'destination': network['destination'], 'auth_utc': auth_utc.isoformat()})
    assert len(answers) == 1
    return answers[0]


async def expect_error(call, expected):
    try:
        await call
    except HTTPException as error:
        assert error.status_code == expected
    else:
        raise AssertionError('La API no rechazó una operación no permitida')


async def catalog_snapshot(session, group_id):
    rows = list((await session.execute(select(Challenge.id, Challenge.code, Challenge.name, Challenge.instructions,
        Challenge.scenario, Challenge.asset_references, Challenge.points, Challenge.is_published)
        .where(Challenge.code.in_(vm_logic.CODES)).order_by(Challenge.code))).all())
    ids = [row.id for row in rows]
    flags = list((await session.execute(select(ChallengeFlag.id, ChallengeFlag.challenge_id, ChallengeFlag.mode,
        ChallengeFlag.is_active).where(ChallengeFlag.challenge_id.in_(ids)).order_by(ChallengeFlag.id))).all())
    assignments = list((await session.execute(select(ChallengeGroupAssignment.id, ChallengeGroupAssignment.challenge_id,
        ChallengeGroupAssignment.group_id).where(ChallengeGroupAssignment.challenge_id.in_(ids),
        ChallengeGroupAssignment.group_id == group_id).order_by(ChallengeGroupAssignment.id))).all())
    return rows, flags, assignments


async def main():
    factory = make_session_factory()
    engine = factory.kw['bind']
    tag = uuid.uuid4().hex[:8]
    guac = make_guacamole_admin()
    connections = await guac.list_connections()
    kali = next(item for item in connections if item.hostname == '10.10.20.10' and item.protocol == 'ssh')
    async with factory() as session:
        group = await session.scalar(select(StudentGroup).where(StudentGroup.code == '45HY'))
        assert group is not None
        real_user = await session.scalar(select(User).join(GroupMembership).where(
            GroupMembership.group_id == group.id, User.role == 'player'))
        assert real_user is not None
        before_catalog = await catalog_snapshot(session, group.id)
    permissions = await guac.get_user_permissions(real_user.username)
    parameters = kali.parameters
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('10.10.20.10', port=int(parameters.get('port') or 22),
        username=parameters['username'], password=parameters['password'], timeout=8, allow_agent=False, look_for_keys=False)
    created_ids = []
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            test_factory = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode='create_savepoint')
            try:
                async with test_factory() as session:
                    await configure(session, group_code='45HY')
                    first = await catalog_snapshot(session, group.id)
                    assert not (await configure(session, group_code='45HY'))['changed']
                    assert await catalog_snapshot(session, group.id) == first
                    assert len(first[0]) == 4
                    user = User(username='qa-vm-logic-' + tag, password_hash='!disabled!', role='player')
                    session.add(user)
                    await session.flush()
                    session.add(GroupMembership(group_id=group.id, user_id=user.id))
                    await session.commit()
                request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
                    session_factory=test_factory,
                    guacamole_admin=SimpleNamespace(list_connections=AsyncMock(return_value=connections),
                        get_user_permissions=AsyncMock(return_value=permissions)),
                    redis=SimpleNamespace(incr=AsyncMock(return_value=1), expire=AsyncMock(), publish=AsyncMock()),
                    sockets=SimpleNamespace(broadcast=AsyncMock()), terminal_sessions=SimpleNamespace(close_run=AsyncMock()))))
                for code in vm_logic.CODES:
                    view = await runs.start_challenge(code, request, user)
                    created_ids.append(view.id)
                    assert (await runs.start_challenge(code, request, user)).id == view.id
                    assert view.workspace_strategy == vm_logic.STRATEGY and view.target_vm_name == 'LAB-KALI'
                    if code == 'WEB-02':
                        async with test_factory() as session:
                            challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
                            challenge.instructions += ' QA stale content'
                            await session.flush()
                            await expect_error(configure(session, group_code='45HY'), 409)
                            await session.rollback()
                    options = await terminal.terminal_options(view.id, request, user)
                    assert 'ssh' in options['protocols']
                    identifier, _, _ = await terminal.authorized_target(request.app, view.id, user.id, 'ssh', 'victim')
                    assert identifier == kali.identifier
                    await expect_error(terminal.authorized_target(request.app, view.id, user.id, 'ssh', 'attacker'), 409)
                    await expect_error(vm_logic_api.info(view.id, request, real_user), 404)
                    info = json.loads((await vm_logic_api.info(view.id, request, user)).body)
                    assert not {'files', 'case', 'expected', 'flag', 'commands'} & set(info)
                    parsed = urlsplit(info['base_url'])
                    assert parsed.hostname == '10.10.30.12' and parsed.port == 18082
                    answer = solve(client, info['base_url'], code)
                    incorrect = dict(answer)
                    incorrect[next(iter(incorrect))] = 'wrong'
                    rejected = json.loads((await vm_logic_api.answer(view.id, incorrect, request, user)).body)
                    assert not rejected['correct'] and rejected['flag'] is None
                    await expect_error(vm_logic_api.answer(view.id, answer, request, real_user), 404)
                    validated = json.loads((await vm_logic_api.answer(view.id, answer, request, user)).body)
                    assert validated['correct'] and validated['flag']
                    awarded = await runs.submit_flag(code, SubmissionRequest(value=validated['flag']), request, user)
                    assert awarded.correct and awarded.awarded_points > 0
                    duplicate = await runs.submit_flag(code, SubmissionRequest(value=validated['flag']), request, user)
                    assert duplicate.correct and duplicate.awarded_points == 0
                    if code == 'DFIR-01':
                        async with test_factory() as session:
                            row = await session.get(ChallengeRun, view.id)
                            row.expires_at = now_utc() - timedelta(seconds=1)
                            await session.commit()
                        await expect_error(vm_logic_api.info(view.id, request, user), 409)
                        await expect_error(vm_logic_api.answer(view.id, answer, request, user), 409)
                    await runs.close_run(view.id, request, user)
                    await expect_error(vm_logic_api.info(view.id, request, user), 409)
                    assert http(client, info['base_url'])['status'] in (404, 410)
                    print('PASS ' + code + ': adquisición desde Kali, análisis, puntos únicos y revocación', flush=True)
            finally:
                await outer.rollback()
    finally:
        client.close()
        cleanup_errors = []
        for run_id in created_ids:
            try:
                await vm_logic.cleanup(SimpleNamespace(id=run_id))
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        async with factory() as session:
            assert await session.scalar(select(User.id).where(User.username == 'qa-vm-logic-' + tag)) is None
            assert await catalog_snapshot(session, group.id) == before_catalog
        await engine.dispose()
        assert not cleanup_errors, 'No se pudo completar la limpieza remota de todas las corridas QA'
    print('PASS rollback VM: catálogo intacto, sin usuarios ni puntos QA persistidos', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
