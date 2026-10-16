"""Prueba HTTP real desde Kali; revierte SQL y elimina las corridas temporales.

No imprime contraseñas, flags ni credenciales de las conexiones Guacamole.
Ejecutar en el contenedor API una vez desplegado el código HTTP nuevo.
"""
import asyncio
import base64
import hashlib
import json
import re
import shlex
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urljoin, urlsplit

import paramiko
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import runs, terminal, vm_logic as vm_logic_api
from app.db import make_session_factory
from app.guacamole import make_guacamole_admin
from app.models import Challenge, ChallengeFlag, ChallengeGroupAssignment, GroupMembership, StudentGroup, User
from app.schemas import SubmissionRequest
from app.services import http_practice
from app.services.http_catalog import configure


WEB_CODE = 'ESC-06-WEBAUTH'
FILES_CODE = 'ESC-07-EXPOSED'


def remote(client, command, stdin=None):
    inp, out, err = client.exec_command(command, timeout=90)
    if stdin is not None:
        inp.write(stdin)
        inp.flush()
        inp.channel.shutdown_write()
    output = out.read().decode()
    status = out.channel.recv_exit_status()
    if status != 0:
        # Los errores del servidor pueden contener material del ejercicio;
        # informar solamente el código de salida, sin volcar los streams.
        err.read()
        raise AssertionError(f'Comando de integración falló con código {status}')
    return output


def http_get(client, url, username=None, password=None):
    headers = {}
    if username is not None:
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers['Authorization'] = 'Basic ' + credentials
    script = (
        'import json, urllib.request, urllib.error\n'
        f'request=urllib.request.Request({url!r},headers={headers!r})\n'
        'try:\n'
        ' response=urllib.request.urlopen(request,timeout=15)\n'
        'except urllib.error.HTTPError as error:\n'
        ' response=error\n'
        'print(json.dumps({"status":response.status,"body":response.read().decode()}))\n'
    )
    return json.loads(remote(client, 'python3 -', script))


async def assert_kali(request, user, run, kali):
    assert run.target_vm_name == 'LAB-KALI'
    options = await terminal.terminal_options(run.id, request, user)
    assert 'ssh' in options['protocols']
    identifier, _, _ = await terminal.authorized_target(
        request.app, run.id, user.id, 'ssh', 'victim'
    )
    assert identifier == kali.identifier
    try:
        await terminal.authorized_target(request.app, run.id, user.id, 'ssh', 'attacker')
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError('El ejercicio permitió otro destino de terminal')


async def award_once(request, user, code, body):
    matches = re.findall(r'FLAG\{[^\r\n}]+\}', body)
    assert len(matches) == 1, 'La evidencia no contiene exactamente una flag'
    result = await runs.submit_flag(code, SubmissionRequest(value=matches[0]), request, user)
    assert result.correct and result.awarded_points > 0
    duplicate = await runs.submit_flag(code, SubmissionRequest(value=matches[0]), request, user)
    assert duplicate.correct and duplicate.awarded_points == 0


async def assert_http_error(call, status):
    try:
        await call
    except HTTPException as error:
        assert error.status_code == status
    else:
        raise AssertionError(f'La API debía rechazar la operación con HTTP {status}')


async def catalog_snapshot(session, group_id):
    challenges = list((await session.execute(select(
        Challenge.id, Challenge.code, Challenge.scenario, Challenge.is_published
    ).where(Challenge.code.in_((WEB_CODE, FILES_CODE))).order_by(Challenge.code))).all())
    ids = [row.id for row in challenges]
    flags = list((await session.execute(select(
        ChallengeFlag.id, ChallengeFlag.challenge_id, ChallengeFlag.mode, ChallengeFlag.is_active
    ).where(ChallengeFlag.challenge_id.in_(ids)).order_by(ChallengeFlag.id))).all())
    assignments = list((await session.execute(select(
        ChallengeGroupAssignment.id, ChallengeGroupAssignment.challenge_id, ChallengeGroupAssignment.group_id
    ).where(ChallengeGroupAssignment.challenge_id.in_(ids), ChallengeGroupAssignment.group_id == group_id)
        .order_by(ChallengeGroupAssignment.id))).all())
    return challenges, flags, assignments


async def main():
    factory = make_session_factory()
    engine = factory.kw['bind']
    tag = uuid.uuid4().hex[:8]
    guac = make_guacamole_admin()
    connections = await guac.list_connections()
    kali = next(c for c in connections if c.hostname == '192.168.146.134' and c.protocol == 'ssh')
    parameters = kali.parameters
    async with factory() as session:
        group = await session.scalar(select(StudentGroup).where(StudentGroup.code == '45HY'))
        assert group is not None, 'Falta el grupo de demostración'
        real_user = await session.scalar(
            select(User).join(GroupMembership).where(GroupMembership.group_id == group.id, User.role == 'player')
        )
        assert real_user is not None
        original_catalog = await catalog_snapshot(session, group.id)
    permissions = await guac.get_user_permissions(real_user.username)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        '192.168.146.134', port=int(parameters.get('port') or 22),
        username=parameters['username'], password=parameters['password'], timeout=8,
        allow_agent=False, look_for_keys=False,
    )
    ids = []
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            test_factory = async_sessionmaker(
                connection, expire_on_commit=False, join_transaction_mode='create_savepoint'
            )
            try:
                async with test_factory() as session:
                    await configure(session, group_code='45HY')
                    first_catalog = await catalog_snapshot(session, group.id)
                    second_result = await configure(session, group_code='45HY')
                    assert not second_result['created']
                    assert await catalog_snapshot(session, group.id) == first_catalog
                    assert all(len(rows) == 2 for rows in first_catalog)
                    assert all(flag.mode == 'dynamic' and flag.is_active for flag in first_catalog[1])
                    user = User(username='qa-http-' + tag, password_hash='!disabled!', role='player')
                    session.add(user)
                    await session.flush()
                    session.add(GroupMembership(group_id=group.id, user_id=user.id))
                    await session.commit()
                print('PASS catálogo HTTP idempotente: dos retos, dos flags y dos asignaciones', flush=True)
                request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
                    session_factory=test_factory,
                    guacamole_admin=SimpleNamespace(
                        list_connections=AsyncMock(return_value=connections),
                        get_user_permissions=AsyncMock(return_value=permissions),
                    ),
                    redis=SimpleNamespace(incr=AsyncMock(return_value=1), expire=AsyncMock(), publish=AsyncMock()),
                    sockets=SimpleNamespace(broadcast=AsyncMock()),
                    terminal_sessions=SimpleNamespace(close_run=AsyncMock()),
                )))

                run = await runs.start_challenge(WEB_CODE, request, user)
                ids.append(run.id)
                reused = await runs.start_challenge(WEB_CODE, request, user)
                assert reused.id == run.id
                await assert_kali(request, user, run, kali)
                await assert_http_error(runs.http_practice_info(run.id, request, real_user), 404)
                info = json.loads((await runs.http_practice_info(run.id, request, user)).body)
                parsed = urlsplit(info['base_url'])
                assert parsed.hostname == '192.168.146.137' and parsed.port == 18082
                assert info['username'] and len(info['wordlist']) == 12
                assert len(set(info['wordlist'])) == 12
                identity = SimpleNamespace(id=run.id, user_id=user.id, workspace_strategy=http_practice.PASSWORD_STRATEGY)
                assert http_practice.flag_for(identity) not in json.dumps(info)
                private_url = urljoin(info['base_url'].rstrip('/') + '/', 'private/flag.txt')
                assert http_get(client, private_url)['status'] == 401
                assert http_get(client, private_url, info['username'], 'definitely-wrong')['status'] == 401
                dictionary_path = f'/tmp/ctf-http-qa-{tag}-{run.id}.txt'
                try:
                    dictionary_command = "printf '%s\\n' " + ' '.join(shlex.quote(w) for w in info['wordlist'])
                    remote(client, dictionary_command + ' > ' + shlex.quote(dictionary_path))
                    resource = urlsplit(private_url).path
                    command = (
                        f'hydra -I -l {shlex.quote(info["username"])} -P {shlex.quote(dictionary_path)} '
                        f'-t 1 -f -s {parsed.port} {parsed.hostname} http-get {shlex.quote(resource)}'
                    )
                    output = remote(client, command)
                    match = re.search(r'password:\s*(\S+)', output)
                    assert match is not None, 'Hydra no encontró la contraseña HTTP del ejercicio'
                    evidence = http_get(client, private_url, info['username'], match[1])
                    assert evidence['status'] == 200
                    await award_once(request, user, WEB_CODE, evidence['body'])
                    await runs.close_run(run.id, request, user)
                    await assert_http_error(runs.http_practice_info(run.id, request, user), 409)
                    assert http_get(client, private_url, info['username'], match[1])['status'] in (404, 410)
                    print('PASS web: Hydra real desde Kali, HTTP Basic, flag, puntos únicos y revocación', flush=True)
                finally:
                    remote(client, 'rm -f -- ' + shlex.quote(dictionary_path))

                run = await runs.start_challenge(FILES_CODE, request, user)
                ids.append(run.id)
                reused = await runs.start_challenge(FILES_CODE, request, user)
                assert reused.id == run.id
                await assert_kali(request, user, run, kali)
                await assert_http_error(runs.http_practice_info(run.id, request, real_user), 404)
                info = json.loads((await runs.http_practice_info(run.id, request, user)).body)
                base_url = info['base_url'].rstrip('/') + '/'
                parsed = urlsplit(base_url)
                assert parsed.hostname == '192.168.146.137' and parsed.port == 18082
                identity = SimpleNamespace(id=run.id, user_id=user.id, workspace_strategy=http_practice.FILES_STRATEGY)
                expected_flag = http_practice.flag_for(identity)
                assert expected_flag not in json.dumps(info)
                index = http_get(client, base_url)
                assert index['status'] == 200 and expected_flag not in index['body']
                robots_url = urljoin(base_url, 'robots.txt')
                robots = http_get(client, robots_url)
                assert robots['status'] == 200 and expected_flag not in robots['body']
                candidates = re.findall(r'^Disallow:\s*(\S+)', robots['body'], re.MULTILINE | re.IGNORECASE)
                assert candidates, 'robots.txt no proporciona una ruta para investigar'
                backup_url = urljoin(base_url, candidates[0])
                backup = http_get(client, backup_url)
                assert backup['status'] == 200 and expected_flag not in backup['body']
                filenames = re.findall(r'href=[\"\'](backup-[^\"\']+\.json)[\"\']', backup['body'], re.IGNORECASE)
                assert len(filenames) == 3, 'El directorio debe ofrecer respaldos y señuelos'
                manifest = json.loads(http_get(client, urljoin(backup_url, 'manifest.json'))['body'])
                answers = []
                for filename in filenames:
                    evidence_url = urljoin(backup_url, filename)
                    evidence = http_get(client, evidence_url)
                    assert evidence['status'] == 200 and expected_flag not in evidence['body']
                    document = json.loads(evidence['body'])
                    if (document['release'] == manifest['current_release']
                            and hashlib.sha256(evidence['body'].encode()).hexdigest() == manifest['sha256']):
                        encoded = bytes.fromhex(''.join(fragment['hex'] for fragment in sorted(document['fragments'], key=lambda row: row['seq'])))
                        answers.append({'backup': filename, 'release': document['release'],
                                        'evidence': bytes(value ^ manifest['key'] for value in encoded).decode()})
                assert len(answers) == 1
                rejected = json.loads((await vm_logic_api.answer(run.id, {**answers[0], 'evidence': 'wrong'}, request, user)).body)
                assert not rejected['correct'] and rejected['flag'] is None
                validated = json.loads((await vm_logic_api.answer(run.id, answers[0], request, user)).body)
                assert validated['correct'] and validated['flag'] == expected_flag
                await award_once(request, user, FILES_CODE, validated['flag'])
                await runs.close_run(run.id, request, user)
                await assert_http_error(runs.http_practice_info(run.id, request, user), 409)
                assert http_get(client, evidence_url)['status'] in (404, 410)
                assert http_get(client, robots_url)['status'] in (404, 410)
                print('PASS archivos: descubrimiento, señuelos, integridad, reconstrucción, puntos únicos y revocación', flush=True)
            finally:
                await transaction.rollback()
    finally:
        client.close()
        for run_id in ids:
            await http_practice.cleanup(SimpleNamespace(id=run_id))
        async with factory() as session:
            assert await session.scalar(select(User.id).where(User.username == 'qa-http-' + tag)) is None
            assert await catalog_snapshot(session, group.id) == original_catalog
        await engine.dispose()
    print('PASS rollback HTTP: catálogo intacto, sin usuarios ni puntos de prueba persistidos', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
