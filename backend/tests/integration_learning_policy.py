"""Aceptación de la política configurable sobre PostgreSQL, con rollback total.

Ejecutar después de la migración y el despliegue. Usa únicamente CTF-LNX-03
en su modalidad offline: no abre conexiones SSH/RDP ni modifica las VMs.
No imprime contraseñas, flags, respuestas ni el contenido privado de las ayudas.
Las funciones de API se invocan con un usuario QA deshabilitado y temporario;
este ensayo no realiza el login ni sustituye las pruebas de autenticación HTTP.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import challenges, runs
from app.core import now_utc
from app.db import make_session_factory
from app.models import (Challenge, ChallengeCompletion, ChallengeGroupAssignment,
                        ChallengeHintReveal, ChallengeLearningProgress, ChallengeRun,
                        GroupMembership, StudentGroup, Submission, User)
from app.schemas import ChallengeCreate


CODE = 'CTF-LNX-03'
ORIGINAL_SOLUTION = 'Explicación QA original, privada hasta que termine el plazo.'
ORIGINAL_HINTS = ('Orientación QA privada inicial.', 'Comprobación QA privada final.')


def decoded(response):
    assert response.headers.get('cache-control') == 'no-store', 'Falta protección de caché de aprendizaje'
    return json.loads(response.body)


async def expect_error(operation, status):
    try:
        await operation
    except HTTPException as error:
        assert error.status_code == status, 'Código de rechazo inesperado'
    else:
        raise AssertionError('La API aceptó una operación antes de tiempo')


def request_for(factory):
    forbidden = AsyncMock(side_effect=AssertionError('El ensayo offline intentó acceder a un servicio de VM'))
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        session_factory=factory,
        redis=SimpleNamespace(incr=AsyncMock(return_value=1), expire=AsyncMock(), publish=AsyncMock()),
        sockets=SimpleNamespace(broadcast=AsyncMock()),
        terminal_sessions=SimpleNamespace(close_run=AsyncMock()),
        guacamole_admin=SimpleNamespace(list_connections=forbidden, get_user_permissions=forbidden),
        guacamole=SimpleNamespace(provision=forbidden, revoke=forbidden),
        flag_injector=SimpleNamespace(inject=forbidden, clear=forbidden),
    )))


async def stored_completions(session):
    return list((await session.execute(select(ChallengeCompletion.id, ChallengeCompletion.user_id,
        ChallengeCompletion.challenge_id, ChallengeCompletion.awarded_points,
        ChallengeCompletion.completed_at).order_by(ChallengeCompletion.id))).all())


async def editable_challenge(session):
    challenge = await session.scalar(select(Challenge).where(Challenge.code == CODE))
    assert challenge is not None and challenge.is_published, 'El reto de aceptación debe estar publicado'
    assert set(challenge.asset_references or []) in ({'OFFLINE-CASE'}, {'OFFLINE-CASE', 'LAB-KALI'}), \
        'El reto de aceptación debe conservar su modalidad offline'
    values = {field: deepcopy(getattr(challenge, field)) for field in ChallengeCreate.model_fields}
    return challenge.id, values


async def main():
    factory = make_session_factory()
    engine = factory.kw['bind']
    username = 'qa-learning-policy-' + uuid.uuid4().hex[:12]
    before_configuration = before_completions = None
    try:
        async with factory() as session:
            group = await session.scalar(select(StudentGroup).where(StudentGroup.code == '45HY', StudentGroup.is_active.is_(True)))
            assert group is not None, 'El grupo de aceptación no está disponible'
            group_id = group.id
            challenge_id, before_configuration = await editable_challenge(session)
            assert await session.scalar(select(ChallengeGroupAssignment.id).where(
                ChallengeGroupAssignment.challenge_id == challenge_id,
                ChallengeGroupAssignment.group_id == group_id)) is not None, 'Falta la asignación del reto al grupo'
            admin = await session.scalar(select(User).where(User.role == 'admin').order_by(User.id))
            assert admin is not None, 'No existe un administrador para el ensayo de edición'
            before_completions = await stored_completions(session)
            assert await session.scalar(select(User.id).where(User.username == username)) is None

        original_policy = {'duration_minutes': 7, 'expired_points_percent': 40,
            'hints': [
                {'title': 'Inicio QA', 'content': ORIGINAL_HINTS[0], 'penalty_percent': 10},
                {'title': 'Verificación QA', 'content': ORIGINAL_HINTS[1], 'penalty_percent': 30},
            ], 'solution_text': ORIGINAL_SOLUTION}
        changed_policy = {'duration_minutes': 90, 'expired_points_percent': 5,
            'hints': [
                {'title': 'Inicio modificado QA', 'content': 'Otro contenido QA.', 'penalty_percent': 50},
                {'title': 'Verificación modificada QA', 'content': 'Otra comprobación QA.', 'penalty_percent': 45},
            ], 'solution_text': 'Explicación QA posterior, ajena a la práctica iniciada.'}

        async with engine.connect() as connection:
            outer = await connection.begin()
            test_factory = async_sessionmaker(connection, expire_on_commit=False,
                join_transaction_mode='create_savepoint')
            request = request_for(test_factory)
            try:
                async with test_factory() as session:
                    learner = User(username=username, password_hash='!disabled!', role='player', is_active=False)
                    session.add(learner)
                    await session.flush()
                    learner_id = learner.id
                    session.add(GroupMembership(group_id=group_id, user_id=learner_id))
                    await session.commit()

                payload = ChallengeCreate(**{**before_configuration, 'learning_policy': original_policy})
                saved = await challenges.update_challenge(CODE, payload, request, admin)
                assert saved.learning_policy.model_dump() == original_policy, 'La edición no guardó la política'
                admin_catalog = await challenges.list_challenges(request, user=admin)
                assert next(item for item in admin_catalog if item.code == CODE).learning_policy.model_dump() == original_policy
                learner_catalog = await challenges.list_challenges(request, user=learner)
                assert next(item for item in learner_catalog if item.code == CODE).learning_policy is None, \
                    'El catálogo del estudiante expuso la configuración privada'

                before_start = now_utc()
                first = await runs.start_challenge(CODE, request, learner)
                after_start = now_utc()
                assert first.workspace_strategy == 'offline_case', 'Se intentó iniciar un servicio de VM'
                assert before_start + timedelta(minutes=7) <= first.expires_at <= after_start + timedelta(minutes=7), \
                    'El plazo real de la corrida no coincide con la duración configurada'
                metadata = decoded(await runs.learning_info(first.id, request, learner))
                base_points = metadata['base_points']
                original_deadline = datetime.fromisoformat(metadata['deadline'])
                assert original_deadline == first.expires_at
                assert metadata['hint_count'] == 2 and len(metadata['hints']) == 2
                assert metadata['expired_points_percent'] == 40 and metadata['available_points'] == base_points
                assert [hint['penalty_percent'] for hint in metadata['hints']] == [10, 30]
                assert all('content' not in hint and not hint['unlocked'] for hint in metadata['hints'])
                assert 'solution' not in metadata and ORIGINAL_SOLUTION not in json.dumps(metadata)
                assert not any(content in json.dumps(metadata) for content in ORIGINAL_HINTS), \
                    'Los metadatos expusieron contenido de pistas cerradas'
                await expect_error(runs.learning_solution(first.id, request, learner), 409)
                await expect_error(runs.learning_hint(first.id, 2, request, learner), 409)
                await expect_error(runs.learning_hint(first.id, 3, request, learner), 404)

                revealed_first = decoded(await runs.learning_hint(first.id, 1, request, learner))
                assert revealed_first['available_points'] == base_points * 90 // 100
                assert revealed_first['hints_used'] == 1
                assert revealed_first['hints'][0]['content'] == ORIGINAL_HINTS[0]
                assert 'content' not in revealed_first['hints'][1]

                changed_payload = ChallengeCreate(**{**before_configuration, 'learning_policy': changed_policy})
                updated = await challenges.update_challenge(CODE, changed_payload, request, admin)
                assert updated.learning_policy.model_dump() == changed_policy
                snapshot = decoded(await runs.learning_info(first.id, request, learner))
                assert snapshot['deadline'] == metadata['deadline'] and snapshot['expired_points_percent'] == 40
                assert [hint['penalty_percent'] for hint in snapshot['hints']] == [10, 30]
                revealed_second = decoded(await runs.learning_hint(first.id, 2, request, learner))
                assert revealed_second['hints'][1]['content'] == ORIGINAL_HINTS[1]
                assert revealed_second['available_points'] == base_points * 60 // 100
                duplicate_hint = decoded(await runs.learning_hint(first.id, 2, request, learner))
                assert duplicate_hint['hints_used'] == 2 and duplicate_hint['available_points'] == revealed_second['available_points']

                await runs.close_run(first.id, request, learner)
                reopened = await runs.start_challenge(CODE, request, learner)
                assert reopened.id != first.id and reopened.expires_at == original_deadline, \
                    'Cerrar y reabrir reinició el plazo de aprendizaje'
                reopened_metadata = decoded(await runs.learning_info(reopened.id, request, learner))
                assert reopened_metadata['hints_used'] == 2 and reopened_metadata['available_points'] == base_points * 60 // 100
                assert reopened_metadata['expired_points_percent'] == 40
                async with test_factory() as session:
                    progress = await session.scalar(select(ChallengeLearningProgress).where(
                        ChallengeLearningProgress.user_id == learner_id,
                        ChallengeLearningProgress.challenge_id == challenge_id))
                    assert progress.policy_snapshot == original_policy and progress.first_run_id == first.id
                    recorded_costs = list((await session.scalars(select(ChallengeHintReveal.penalty_percent)
                        .where(ChallengeHintReveal.progress_id == progress.id).order_by(ChallengeHintReveal.hint_id))).all())
                    assert recorded_costs == [10, 30]
                    # Se simula el reloj exclusivamente en filas QA dentro del rollback.
                    progress.deadline = now_utc() - timedelta(seconds=1)
                    qa_runs = (await session.scalars(select(ChallengeRun).where(ChallengeRun.user_id == learner_id))).all()
                    assert len(qa_runs) == 2 and all(item.challenge_id == challenge_id for item in qa_runs)
                    for row in qa_runs:
                        row.expires_at = progress.deadline
                    await session.commit()

                expired = decoded(await runs.learning_info(reopened.id, request, learner))
                assert expired['expired'] and expired['available_points'] == base_points * 40 // 100
                assert 'solution' not in expired
                await expect_error(runs.learning_complete(reopened.id, request, learner), 409)
                await expect_error(runs.learning_hint(reopened.id, 1, request, learner), 409)
                solution = decoded(await runs.learning_solution(reopened.id, request, learner))
                assert solution['solution']['steps'] == [ORIGINAL_SOLUTION], \
                    'La solución no conservó el contenido de la política original'
                assert solution['expired_points_percent'] == 40
                assert solution['solution_revealed'] and solution['available_points'] == base_points * 40 // 100
                completed = decoded(await runs.learning_complete(reopened.id, request, learner))
                duplicate = decoded(await runs.learning_complete(reopened.id, request, learner))
                assert completed['challenge_completed'] and completed['awarded_points'] == base_points * 40 // 100
                assert duplicate['challenge_completed'] and duplicate['awarded_points'] == 0
                async with test_factory() as session:
                    qa_completions = (await session.scalars(select(ChallengeCompletion).where(
                        ChallengeCompletion.user_id == learner_id))).all()
                    assert len(qa_completions) == 1 and qa_completions[0].awarded_points == base_points * 40 // 100
                    assert await session.scalar(select(Submission.id).where(Submission.user_id == learner_id)) is None, \
                        'El repaso asistido creó un envío de flag ficticio'
                    progress = await session.scalar(select(ChallengeLearningProgress).where(
                        ChallengeLearningProgress.user_id == learner_id,
                        ChallengeLearningProgress.challenge_id == challenge_id))
                    assert progress.is_assisted
                print('PASS política configurable: plazo real, privacidad, pistas con costes propios y snapshot estable', flush=True)
                print('PASS aprendizaje: solución al vencer, crédito configurado y registro único de puntos', flush=True)
            finally:
                await outer.rollback()

        async with factory() as session:
            _, after_configuration = await editable_challenge(session)
            assert after_configuration == before_configuration, 'El rollback no restauró la configuración del reto'
            assert await stored_completions(session) == before_completions, 'Se modificaron resultados persistidos'
            assert await session.scalar(select(User.id).where(User.username == username)) is None, 'Quedó un usuario QA persistido'
            assert await session.scalar(select(ChallengeRun.id).where(ChallengeRun.user_id == learner_id)) is None, 'Quedó una corrida QA persistida'
            assert await session.scalar(select(ChallengeLearningProgress.id).where(
                ChallengeLearningProgress.user_id == learner_id)) is None, 'Quedó un progreso QA persistido'
        print('PASS rollback PostgreSQL: configuración y resultados intactos, sin usuario ni datos QA', flush=True)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
