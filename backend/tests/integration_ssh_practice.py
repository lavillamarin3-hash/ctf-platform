"""Aceptación SSH real Kali → LNX-VICT, independiente del catálogo offline.

Usa el reto ESC-02 publicado y asignado a 45HY; no configura el catálogo ni
concede permisos Guacamole. La cuenta QA no tiene una credencial utilizable y
sus filas nunca se confirman fuera de la transacción de prueba. Todos sus datos
SQL se revierten. Solo se provisiona y elimina su registro de
práctica. Contraseñas, salida de Hydra y flags permanecen en memoria.
Ejecutar después de desplegar la API, con PYTHONPATH=/app.
"""
import asyncio
from contextlib import suppress
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import paramiko
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import runs, terminal
from app.db import make_session_factory
from app.guacamole import make_guacamole_admin
from app.models import (Challenge, ChallengeCompletion, ChallengeGroupAssignment,
                        ChallengeLearningProgress, ChallengeRun, GroupMembership,
                        StudentGroup, User)
from app.schemas import SubmissionRequest
from app.services import ssh_practice


KALI_HOST = '192.168.146.134'


def remote(client, script, *, timeout=120):
    """Ejecuta Python por stdin; nunca incluye los streams en los errores."""
    inp, out, err = client.exec_command('python3 -', timeout=timeout)
    inp.write(script)
    inp.flush()
    inp.channel.shutdown_write()
    output = out.read().decode()
    status = out.channel.recv_exit_status()
    if status != 0:
        err.read()
        raise AssertionError(f'Falló una comprobación remota SSH, código {status}; salida omitida')
    try:
        return json.loads(output)
    except (TypeError, ValueError):
        raise AssertionError('La comprobación remota no devolvió el formato esperado; salida omitida') from None


def login_probe(client, username, password):
    script = (
        'import json,paramiko\n'
        'client=paramiko.SSHClient()\n'
        'client.set_missing_host_key_policy(paramiko.AutoAddPolicy())\n'
        'try:\n'
        f' client.connect({ssh_practice.HOST!r},port={ssh_practice.PORT},username={username!r},password={password!r},'
        'timeout=8,banner_timeout=8,auth_timeout=8,allow_agent=False,look_for_keys=False)\n'
        ' _,out,_=client.exec_command("cat flag.txt",timeout=10)\n'
        ' evidence=out.read().decode().strip()\n'
        ' print(json.dumps({"authenticated":True,"evidence":evidence}))\n'
        'except paramiko.AuthenticationException:\n'
        ' print(json.dumps({"authenticated":False,"evidence":None}))\n'
        'except Exception as error:\n'
        ' print(json.dumps({"error":type(error).__name__}))\n'
        'finally:\n'
        ' client.close()\n'
    )
    result = remote(client, script)
    assert 'error' not in result, 'La comprobación SSH no pudo alcanzar el servicio de práctica'
    return result


def write_dictionary(client, path, words):
    with client.open_sftp() as sftp:
        with sftp.open(path, 'w') as file:
            file.write('\n'.join(words) + '\n')
        sftp.chmod(path, 0o600)


def remove_dictionary(client, path):
    with client.open_sftp() as sftp:
        with suppress(FileNotFoundError):
            sftp.remove(path)


def hydra_probe(client, username, dictionary_path, tag):
    # Un directorio propio evita compartir hydra.restore con estudiantes.
    arguments = ['hydra', '-I', '-l', username, '-P', dictionary_path, '-t', '1', '-f',
                 '-s', str(ssh_practice.PORT), ssh_practice.HOST, 'ssh']
    script = (
        'import json,re,subprocess,tempfile\n'
        'try:\n'
        f' with tempfile.TemporaryDirectory(prefix={"ctf-ssh-hydra-" + tag + "-"!r}) as scratch:\n'
        f'  result=subprocess.run({arguments!r},cwd=scratch,capture_output=True,text=True,timeout=90)\n'
        '  match=re.search(r"password:\\s*(\\S+)",result.stdout)\n'
        '  print(json.dumps({"status":result.returncode,"password":match[1] if match else None}))\n'
        'except Exception as error:\n'
        ' print(json.dumps({"error":type(error).__name__}))\n'
    )
    result = remote(client, script)
    assert 'error' not in result and result.get('status') == 0, 'Hydra no pudo completar el ensayo autorizado; salida omitida'
    assert result.get('password'), 'Hydra no encontró la contraseña de práctica; salida omitida'
    return result['password']


async def expect_error(operation, status):
    try:
        await operation
    except HTTPException as error:
        assert error.status_code == status, 'La API rechazó la operación con un código inesperado'
    else:
        raise AssertionError('La API permitió una operación de otro usuario o de una corrida cerrada')


async def completion_snapshot(session):
    return list((await session.execute(select(ChallengeCompletion.id, ChallengeCompletion.user_id,
        ChallengeCompletion.challenge_id, ChallengeCompletion.awarded_points,
        ChallengeCompletion.completed_at).order_by(ChallengeCompletion.id))).all())


async def challenge_snapshot(session):
    return (await session.execute(select(Challenge.id, Challenge.code, Challenge.scenario,
        Challenge.asset_references, Challenge.points, Challenge.is_published,
        Challenge.learning_policy).where(Challenge.code == ssh_practice.CODE))).one()


async def main():
    factory = make_session_factory()
    engine = factory.kw['bind']
    tag = uuid.uuid4().hex[:12]
    username = 'qa-ssh-practice-' + tag
    client = paramiko.SSHClient()
    # Mantiene la política de claves de host de integration_vm_catalog.py.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    run_ids = []
    dictionary_paths = []
    learner_id = None
    cleanup_errors = []
    try:
        guac = make_guacamole_admin()
        connections = await guac.list_connections()
        kali = next(item for item in connections if item.hostname == KALI_HOST and item.protocol == 'ssh')
        async with factory() as session:
            group = await session.scalar(select(StudentGroup).where(
                StudentGroup.code == '45HY', StudentGroup.is_active.is_(True)))
            assert group is not None, 'Falta el grupo activo de demostración'
            group_id = group.id
            original_challenge = await challenge_snapshot(session)
            assert original_challenge.is_published and original_challenge.scenario == 'SSH-PASSWORD-LAB', \
                'El reto SSH debe estar publicado y configurado antes del ensayo'
            assert await session.scalar(select(ChallengeGroupAssignment.id).where(
                ChallengeGroupAssignment.challenge_id == original_challenge.id,
                ChallengeGroupAssignment.group_id == group_id)) is not None, 'El reto SSH no está asignado al grupo'
            real_user = await session.scalar(select(User).join(GroupMembership).where(
                GroupMembership.group_id == group_id, User.role == 'player', User.is_active.is_(True))
                .order_by(User.id))
            assert real_user is not None, 'Falta un estudiante del grupo con permisos de laboratorio'
            original_completions = await completion_snapshot(session)
            assert await session.scalar(select(User.id).where(User.username == username)) is None
        permissions = await guac.get_user_permissions(real_user.username)
        parameters = kali.parameters
        await asyncio.to_thread(client.connect, KALI_HOST, port=int(parameters.get('port') or 22),
            username=parameters['username'], password=parameters['password'], timeout=8,
            banner_timeout=8, auth_timeout=8, allow_agent=False, look_for_keys=False)

        async with engine.connect() as connection:
            outer = await connection.begin()
            test_factory = async_sessionmaker(connection, expire_on_commit=False,
                join_transaction_mode='create_savepoint')
            try:
                async with test_factory() as session:
                    learner = User(username=username, password_hash='!disabled!', role='player', is_active=True)
                    session.add(learner)
                    await session.flush()
                    learner_id = learner.id
                    session.add(GroupMembership(group_id=group_id, user_id=learner_id))
                    await session.commit()
                request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
                    session_factory=test_factory,
                    guacamole_admin=SimpleNamespace(list_connections=AsyncMock(return_value=connections),
                        get_user_permissions=AsyncMock(return_value=permissions)),
                    redis=SimpleNamespace(incr=AsyncMock(return_value=1), expire=AsyncMock(), publish=AsyncMock()),
                    sockets=SimpleNamespace(broadcast=AsyncMock()),
                    terminal_sessions=SimpleNamespace(close_run=AsyncMock()),
                )))
                run = await runs.start_challenge(ssh_practice.CODE, request, learner)
                run_ids.append(run.id)
                assert run.workspace_strategy == 'ssh_password_lab' and run.target_vm_name == 'LAB-KALI'
                assert (await runs.start_challenge(ssh_practice.CODE, request, learner)).id == run.id
                identity = SimpleNamespace(id=run.id, user_id=learner_id)
                # Caso borde acotado: únicamente la última de 12 candidatas permite entrar.
                await asyncio.to_thread(ssh_practice.provision, run.id, f'ctf{run.id}',
                    ssh_practice.WORDS[-1], ssh_practice.flag_for(identity), run.expires_at.timestamp())
                info_response = await runs.ssh_practice_info(run.id, request, learner)
                assert info_response.headers.get('cache-control') == 'no-store'
                info = json.loads(info_response.body)
                assert info['target'] == f'{ssh_practice.HOST}:{ssh_practice.PORT}'
                assert info['username'] == f'ctf{run.id}' and info['commands'] == []
                assert info['wordlist'] == ssh_practice.WORDS and len(set(info['wordlist'])) == 12
                assert ssh_practice.flag_for(identity) not in json.dumps(info)
                await expect_error(runs.ssh_practice_info(run.id, request, real_user), 404)
                options = await terminal.terminal_options(run.id, request, learner)
                assert 'ssh' in options['protocols']
                target, _, _ = await terminal.authorized_target(request.app, run.id, learner_id, 'ssh', 'victim')
                assert target == kali.identifier
                await expect_error(terminal.authorized_target(request.app, run.id, learner_id, 'ssh', 'attacker'), 409)
                rejected = await asyncio.to_thread(login_probe, client, info['username'], 'definitely-wrong')
                assert not rejected['authenticated'] and rejected['evidence'] is None

                dictionary_path = f'/tmp/ctf-ssh-qa-{tag}-{run.id}.txt'
                dictionary_paths.append(dictionary_path)
                await asyncio.to_thread(write_dictionary, client, dictionary_path, info['wordlist'])
                found = await asyncio.to_thread(hydra_probe, client, info['username'], dictionary_path, tag)
                assert found == ssh_practice.WORDS[-1], 'La contraseña encontrada no corresponde al caso borde'
                accepted = await asyncio.to_thread(login_probe, client, info['username'], found)
                assert accepted['authenticated'] and accepted['evidence'] == ssh_practice.flag_for(identity), \
                    'La sesión no pudo leer la evidencia original de su corrida'
                response = await runs.submit_flag(ssh_practice.CODE,
                    SubmissionRequest(value=accepted['evidence']), request, learner)
                assert response.correct and response.challenge_completed and response.awarded_points == original_challenge.points
                duplicate = await runs.submit_flag(ssh_practice.CODE,
                    SubmissionRequest(value=accepted['evidence']), request, learner)
                assert duplicate.correct and duplicate.challenge_completed and duplicate.awarded_points == 0
                async with test_factory() as session:
                    completed = (await session.scalars(select(ChallengeCompletion).where(
                        ChallengeCompletion.user_id == learner_id))).all()
                    assert len(completed) == 1 and completed[0].awarded_points == original_challenge.points
                await runs.close_run(run.id, request, learner)
                await expect_error(runs.ssh_practice_info(run.id, request, learner), 409)
                revoked = await asyncio.to_thread(login_probe, client, info['username'], found)
                assert not revoked['authenticated'] and revoked['evidence'] is None
                print('PASS SSH real desde Kali: rechazo inicial, Hydra de 12 candidatas, evidencia y puntos únicos', flush=True)
                print('PASS cierre SSH: registro revocado y evidencia inaccesible', flush=True)
            finally:
                await outer.rollback()
    finally:
        # La limpieza intenta todos los recursos aunque una comprobación falle.
        for path in dictionary_paths:
            try:
                await asyncio.to_thread(remove_dictionary, client, path)
            except Exception as error:
                cleanup_errors.append('diccionario:' + type(error).__name__)
        for run_id in run_ids:
            try:
                await ssh_practice.cleanup(SimpleNamespace(id=run_id))
            except Exception as error:
                cleanup_errors.append('registro:' + type(error).__name__)
        client.close()
        try:
            if learner_id is not None:
                async with factory() as session:
                    assert await session.scalar(select(User.id).where(User.username == username)) is None, 'Quedó un usuario QA'
                    assert await completion_snapshot(session) == original_completions, 'Se alteraron resultados persistidos'
                    assert await challenge_snapshot(session) == original_challenge, 'Se alteró la configuración del reto SSH'
                    assert await session.scalar(select(ChallengeRun.id).where(ChallengeRun.user_id == learner_id)) is None, 'Quedó una corrida QA'
                    assert await session.scalar(select(ChallengeLearningProgress.id).where(
                        ChallengeLearningProgress.user_id == learner_id)) is None, 'Quedó progreso QA'
        finally:
            await engine.dispose()
        assert not cleanup_errors, 'Falló la limpieza de recursos QA: ' + ', '.join(cleanup_errors)
    print('PASS rollback PostgreSQL: resultados y catálogo intactos, sin usuario ni datos QA', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
