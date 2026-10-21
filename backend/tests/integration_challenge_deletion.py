"""Aceptación PostgreSQL: elimina solo un reto QA y revierte TODO al terminar.

Ejecutar desde backend con PYTHONPATH=/app:
    python tests/integration_challenge_deletion.py

No borra retos reales, no toca VMs/Guacamole/Redis y no imprime flags ni datos
de usuarios. Las dependencias HTTP/roles se prueban en test_challenge_deletion;
aquí se invocan los handlers con identidad QA en una transacción externa y
savepoints para comprobar los FKs y el rollback de PostgreSQL real.
"""
import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.challenges import permanently_delete_challenge, preview_challenge_deletion
from app.core import now_utc
from app.db import make_session_factory
from app.models import (AuditEvent, Challenge, ChallengeCompletion, ChallengeFlag,
                        ChallengeGroupAssignment, ChallengeHintReveal, ChallengeInstance,
                        ChallengeLearningProgress, ChallengeRun, ChallengeRunFlag,
                        GroupMembership, Laboratory, RemoteAccessAssignment, StudentGroup,
                        Submission, User, VMAsset)
from app.schemas import ChallengePermanentDeleteRequest
from app.services.challenge_deletion import deleted_codes


GRAPH = (Challenge, ChallengeRun, ChallengeFlag, ChallengeRunFlag, RemoteAccessAssignment,
         ChallengeInstance, ChallengeHintReveal, ChallengeLearningProgress, Submission,
         ChallengeCompletion, ChallengeGroupAssignment)
PRESERVED = (User, StudentGroup, GroupMembership, Laboratory, VMAsset)


async def snapshot(session):
    return {
        'counts': {model.__tablename__: int(await session.scalar(select(func.count()).select_from(model)))
                   for model in (*GRAPH, *PRESERVED, AuditEvent)},
        'completions': list((await session.execute(select(
            ChallengeCompletion.id, ChallengeCompletion.user_id, ChallengeCompletion.challenge_id,
            ChallengeCompletion.awarded_points, ChallengeCompletion.completed_at)
            .order_by(ChallengeCompletion.id))).all()),
    }


async def make_graph(session, *, code, points, admin_id, player_id, group_id, vm_id):
    now = now_utc()
    challenge = Challenge(code=code, name='Prueba aislada de eliminación',
        description='Datos QA temporales; rollback obligatorio.', instructions='', difficulty='Básico',
        category='WEB', mitre_technique='T1110', asset_references=['OFFLINE-CASE'],
        points=points, created_by=admin_id, is_published=True)
    session.add(challenge)
    await session.flush()
    flag = ChallengeFlag(challenge_id=challenge.id, label='Evidencia QA', mode='static',
                         flag_hash='!not-a-real-flag!', flag_order=1, is_active=True)
    run = ChallengeRun(challenge_id=challenge.id, user_id=player_id, status='closed',
        workspace_strategy='offline_case', started_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1), closed_at=now - timedelta(minutes=50))
    session.add_all([flag, run])
    await session.flush()
    progress = ChallengeLearningProgress(user_id=player_id, challenge_id=challenge.id,
        first_run_id=run.id, base_points=points, deadline=run.expires_at, policy_version=1)
    session.add(progress)
    await session.flush()
    session.add_all([
        ChallengeRunFlag(run_id=run.id, flag_id=flag.id, flag_hash='!not-a-real-flag!', fingerprint='qa-only'),
        RemoteAccessAssignment(run_id=run.id, external_reference='qa-' + code,
            launch_url='https://terminal.invalid/', status='revoked', expires_at=run.expires_at),
        ChallengeInstance(challenge_id=challenge.id, vm_asset_id=vm_id, state='disponible'),
        Submission(challenge_id=challenge.id, user_id=player_id, flag_id=flag.id,
            submitted_value_hmac='qa-only', is_correct=True),
        ChallengeCompletion(challenge_id=challenge.id, user_id=player_id, awarded_points=points),
        ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group_id, created_by=admin_id),
        ChallengeHintReveal(progress_id=progress.id, run_id=run.id, hint_id=1, penalty_percent=10),
    ])
    await session.flush()
    return challenge.id, run.id


async def expect_error(coroutine, expected):
    try:
        await coroutine
    except HTTPException as error:
        assert error.status_code == expected, 'Código de rechazo inesperado'
    else:
        raise AssertionError('Se aceptó una eliminación que debía rechazarse')


async def main():
    factory = make_session_factory()
    engine = factory.kw['bind']
    suffix = uuid.uuid4().hex[:12].upper()
    code = 'QA-DELETE-' + suffix
    keep_code = 'QA-KEEP-' + suffix
    before = None
    try:
        async with factory() as session:
            before = await snapshot(session)
        async with engine.connect() as connection:
            outer = await connection.begin()
            test_factory = async_sessionmaker(connection, expire_on_commit=False,
                join_transaction_mode='create_savepoint')
            request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=test_factory)))
            try:
                async with test_factory() as session:
                    admin = User(username='qa-del-admin-' + suffix, role='admin', password_hash='!disabled!', is_active=False)
                    player = User(username='qa-del-player-' + suffix, role='player', password_hash='!disabled!', is_active=False)
                    group = StudentGroup(code='QA-' + suffix, name='Grupo temporal ' + suffix)
                    lab = Laboratory(code='QA-' + suffix, name='Laboratorio temporal ' + suffix)
                    session.add_all([admin, player, group, lab])
                    await session.flush()
                    vm = VMAsset(laboratory_id=lab.id, name='QA-VM-' + suffix)
                    keep_vm = VMAsset(laboratory_id=lab.id, name='QA-KEEP-VM-' + suffix)
                    session.add_all([vm, keep_vm, GroupMembership(group_id=group.id, user_id=player.id)])
                    await session.flush()
                    target_id, run_id = await make_graph(session, code=code, points=100,
                        admin_id=admin.id, player_id=player.id, group_id=group.id, vm_id=vm.id)
                    keep_id, keep_run_id = await make_graph(session, code=keep_code, points=200,
                        admin_id=admin.id, player_id=player.id, group_id=group.id, vm_id=keep_vm.id)
                    admin_id, player_id, group_id, lab_id, vm_id, keep_vm_id = (
                        admin.id, player.id, group.id, lab.id, vm.id, keep_vm.id)
                    await session.commit()
                actor = SimpleNamespace(id=admin_id, role='admin')
                payload = ChallengePermanentDeleteRequest(confirm_code=code)

                preview = await preview_challenge_deletion(code, request, actor)
                assert preview['can_delete'] and preview['counts']['awarded_points'] == 100
                assert len(preview['counts']) == 11
                assert all(value == 1 for name, value in preview['counts'].items() if name != 'awarded_points')
                await expect_error(permanently_delete_challenge(code,
                    ChallengePermanentDeleteRequest(confirm_code=keep_code), request, actor), 422)

                # Un vencimiento no confirma la limpieza. El rechazo conserva
                # todo el grafo aun cuando una vista previa anterior permitía borrar.
                async with test_factory() as session:
                    run = await session.get(ChallengeRun, run_id)
                    run.status = 'active'
                    await session.commit()
                await expect_error(permanently_delete_challenge(code, payload, request, actor), 409)
                async with test_factory() as session:
                    run = await session.get(ChallengeRun, run_id)
                    run.status = 'closed'
                    await session.commit()
                print('PASS PostgreSQL: vista previa, confirmación exacta y bloqueo de limpieza pendiente')

                # Error después de DELETEs SQL, antes del commit: todos los FKs
                # y registros deben recuperarse por rollback del savepoint.
                with patch('app.api.challenges.write_audit', new_callable=AsyncMock,
                           side_effect=RuntimeError('Fallo QA controlado antes de commit')):
                    try:
                        await permanently_delete_challenge(code, payload, request, actor)
                    except RuntimeError:
                        pass
                    else:
                        raise AssertionError('No se propagó el fallo QA controlado')
                assert (await preview_challenge_deletion(code, request, actor))['counts'] == preview['counts']
                print('PASS PostgreSQL: rollback restaura el grafo completo ante fallo de auditoría')

                result = await permanently_delete_challenge(code, payload, request, actor)
                assert result['deleted'] and result['counts'] == preview['counts']
                await expect_error(preview_challenge_deletion(code, request, actor), 404)
                async with test_factory() as session:
                    assert await session.get(Challenge, keep_id) is not None
                    assert await session.get(ChallengeRun, keep_run_id) is not None
                    for model, identifier in ((User, admin_id), (User, player_id), (StudentGroup, group_id),
                                              (Laboratory, lab_id), (VMAsset, vm_id), (VMAsset, keep_vm_id)):
                        assert await session.get(model, identifier) is not None
                    assert await session.scalar(select(ChallengeCompletion.awarded_points).where(
                        ChallengeCompletion.challenge_id == keep_id)) == 200
                    audit = await session.scalar(select(AuditEvent).where(AuditEvent.action == 'challenge.delete',
                                                                         AuditEvent.entity_id == str(target_id)))
                    assert audit is not None and audit.actor_id == admin_id
                    assert audit.details['code'] == code and audit.details['counts'] == preview['counts']
                    assert code in await deleted_codes(session)
                print('PASS PostgreSQL: borrado definitivo de un reto, FKs, puntos y auditoría; otros datos intactos')
            finally:
                await outer.rollback()
        async with factory() as session:
            assert await snapshot(session) == before, 'El rollback dejó diferencias en la base real'
            assert await session.scalar(select(Challenge.id).where(Challenge.code.in_((code, keep_code)))) is None
        print('PASS rollback total: sin usuarios, retos, historial ni puntos QA persistidos')
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
