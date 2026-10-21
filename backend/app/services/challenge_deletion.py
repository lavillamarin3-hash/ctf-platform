"""Vista previa y borrado transaccional del grafo de un único reto.

No cierra laboratorios ni modifica usuarios, grupos, inventario o VMs. Un
laboratorio pendiente debe cerrarse mediante su ciclo normal antes de borrar.
El llamador conserva el lock de Challenge desde la comprobación hasta commit;
start_challenge utiliza el mismo lock antes de crear recursos.
"""
from __future__ import annotations

from sqlalchemy import delete, func, or_, select

from ..models import (
    AuditEvent, Challenge, ChallengeCompletion, ChallengeFlag, ChallengeGroupAssignment,
    ChallengeHintReveal, ChallengeInstance, ChallengeLearningProgress,
    ChallengeRun, ChallengeRunFlag, RemoteAccessAssignment, Submission,
)


async def deleted_codes(session) -> set[str]:
    """Tombstones sin tabla nueva: el seed nunca resucita un reto eliminado.

    La lectura del JSON en Python mantiene compatibilidad con PostgreSQL y con
    SQLite en pruebas. Crear manualmente un reto con ese código sigue siendo una
    decisión explícita del administrador; los catálogos automáticos lo omiten.
    """
    details = (await session.execute(select(AuditEvent.details).where(
        AuditEvent.action == 'challenge.delete', AuditEvent.entity_type == 'challenge'))).scalars().all()
    return {value['code'] for value in details
            if isinstance(value, dict) and isinstance(value.get('code'), str)}


def graph_filters(challenge_id: int):
    """Incluye dependientes por cualquiera de sus claves hacia el reto."""
    runs = select(ChallengeRun.id).where(ChallengeRun.challenge_id == challenge_id)
    flags = select(ChallengeFlag.id).where(ChallengeFlag.challenge_id == challenge_id)
    progress = select(ChallengeLearningProgress.id).where(
        ChallengeLearningProgress.challenge_id == challenge_id)
    return {
        'hint_reveals': (ChallengeHintReveal, or_(
            ChallengeHintReveal.progress_id.in_(progress), ChallengeHintReveal.run_id.in_(runs))),
        'learning_progress': (ChallengeLearningProgress, ChallengeLearningProgress.challenge_id == challenge_id),
        'run_flags': (ChallengeRunFlag, or_(ChallengeRunFlag.run_id.in_(runs), ChallengeRunFlag.flag_id.in_(flags))),
        'remote_access_assignments': (RemoteAccessAssignment, RemoteAccessAssignment.run_id.in_(runs)),
        'instances': (ChallengeInstance, ChallengeInstance.challenge_id == challenge_id),
        'submissions': (Submission, or_(Submission.challenge_id == challenge_id, Submission.flag_id.in_(flags))),
        'completions': (ChallengeCompletion, ChallengeCompletion.challenge_id == challenge_id),
        'group_assignments': (ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == challenge_id),
        'runs': (ChallengeRun, ChallengeRun.challenge_id == challenge_id),
        'flags': (ChallengeFlag, ChallengeFlag.challenge_id == challenge_id),
    }


async def deletion_preview(session, challenge: Challenge) -> dict:
    counts = {}
    for name, (model, condition) in graph_filters(challenge.id).items():
        counts[name] = int(await session.scalar(select(func.count()).select_from(model).where(condition)) or 0)
    counts['awarded_points'] = int(await session.scalar(select(
        func.coalesce(func.sum(ChallengeCompletion.awarded_points), 0)).where(
            ChallengeCompletion.challenge_id == challenge.id)) or 0)

    blockers = []
    pending_runs = int(await session.scalar(select(func.count()).select_from(ChallengeRun).where(
        ChallengeRun.challenge_id == challenge.id,
        # Un plazo vencido no confirma limpieza física; solo closed/expired
        # son estados que el flujo de cierre persiste tras limpiar recursos.
        ChallengeRun.status.not_in(('closed', 'expired')),
    )) or 0)
    if pending_runs:
        blockers.append({'type': 'active_runs', 'count': pending_runs,
            'message': 'Cierra y limpia las corridas activas o pendientes del reto antes de eliminarlo.'})

    run_ids = select(ChallengeRun.id).where(ChallengeRun.challenge_id == challenge.id)
    pending_access = int(await session.scalar(select(func.count()).select_from(RemoteAccessAssignment).where(
        RemoteAccessAssignment.run_id.in_(run_ids),
        RemoteAccessAssignment.status.not_in(('revoked', 'expired')),
    )) or 0)
    if pending_access:
        blockers.append({'type': 'pending_access_cleanup', 'count': pending_access,
            'message': 'Hay accesos remotos pendientes de revocación. Completa la limpieza del laboratorio.'})

    pending_instances = int(await session.scalar(select(func.count()).select_from(ChallengeInstance).where(
        or_(ChallengeInstance.challenge_id == challenge.id, ChallengeInstance.run_id.in_(run_ids)),
        or_(ChallengeInstance.state != 'disponible', ChallengeInstance.run_id.is_not(None),
            ChallengeInstance.user_id.is_not(None), ChallengeInstance.guacamole_access_granted.is_(True),
            ChallengeInstance.last_error.is_not(None)),
    )) or 0)
    if pending_instances:
        blockers.append({'type': 'pending_instance_cleanup', 'count': pending_instances,
            'message': 'Hay instancias reservadas o con limpieza pendiente. Libéralas antes de eliminar el reto.'})

    return {'code': challenge.code, 'name': challenge.name, 'counts': counts,
            'blockers': blockers, 'can_delete': not blockers}


async def delete_graph(session, challenge_id: int) -> None:
    """Borra hijos antes que padres, también donde los FKs no tienen CASCADE.

    El orden es intencional: conserva los subqueries de run/flag/progress hasta
    haber eliminado sus hijos. Core evita la carga implícita de relaciones ORM.
    No hace commit: auditoría y eliminación pertenecen a la misma transacción.
    """
    for model, condition in graph_filters(challenge_id).values():
        await session.execute(delete(model).where(condition).execution_options(synchronize_session=False))
    await session.execute(delete(Challenge).where(Challenge.id == challenge_id)
                          .execution_options(synchronize_session=False))
