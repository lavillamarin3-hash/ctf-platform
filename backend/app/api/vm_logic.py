"""Objetivos y resultados VM; las evidencias solo se adquieren en la víctima."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select

from ..core import now_utc, require_roles
from ..models import Challenge, ChallengeRun, ChallengeGroupAssignment, GroupMembership, StudentGroup
from ..services import http_practice, vm_logic
from ..services.bootstrap import check_rate_limit

router = APIRouter()


async def _case_run(session, run_id, user):
    run = await session.scalar(select(ChallengeRun).where(
        ChallengeRun.id == run_id, ChallengeRun.user_id == user.id).with_for_update())
    if run is None:
        raise HTTPException(404, 'Ejercicio no disponible')
    challenge = await session.get(Challenge, run.challenge_id)
    assigned = await session.scalar(select(ChallengeGroupAssignment.id)
        .join(GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id)
        .join(StudentGroup, StudentGroup.id == GroupMembership.group_id)
        .where(ChallengeGroupAssignment.challenge_id == run.challenge_id,
               GroupMembership.user_id == user.id, StudentGroup.is_active.is_(True)).limit(1))
    vm_case = challenge and challenge.code in vm_logic.CODES and run.workspace_strategy == vm_logic.STRATEGY
    files_case = challenge and challenge.code == http_practice.FILES_CODE and run.workspace_strategy == http_practice.FILES_STRATEGY
    if not challenge or not challenge.is_published or assigned is None or not (vm_case or files_case):
        raise HTTPException(404, 'Ejercicio no disponible')
    if run.status != 'active' or run.expires_at <= now_utc():
        raise HTTPException(409, 'Inicia una corrida vigente para consultar el ejercicio')
    if vm_case and (challenge.scenario != vm_logic.EXPECTED_SCENARIOS[challenge.code]
                    or set(challenge.asset_references or []) != {'LAB-KALI', 'LAB-LNXVICT'}):
        raise HTTPException(409, 'La configuración del ejercicio VM no coincide')
    if files_case and (challenge.scenario != 'HTTP-EXPOSED-FILES-LAB'
                       or set(challenge.asset_references or []) != {'LAB-KALI', 'LAB-LNXVICT'}):
        raise HTTPException(409, 'La configuración del ejercicio HTTP no coincide')
    return run, challenge


@router.get('/api/v1/runs/{run_id}/vm-logic')
async def info(run_id: int, request: Request, user=Depends(require_roles('player'))):
    async with request.app.state.session_factory() as session:
        run, challenge = await _case_run(session, run_id, user)
        result = http_practice.instructions(run) if challenge.code == http_practice.FILES_CODE else vm_logic.metadata(run, challenge.code)
        return JSONResponse(result, headers={'Cache-Control': 'no-store'})


@router.post('/api/v1/runs/{run_id}/vm-logic/answer')
async def answer(run_id: int, payload: dict[str, Annotated[str, Field(max_length=512)]], request: Request,
                 user=Depends(require_roles('player'))):
    await check_rate_limit(request.app.state.redis, f'rate:vm-logic:{user.id}:{run_id}', maximum=8)
    if len(payload) > 8:
        raise HTTPException(422, 'La respuesta contiene demasiados campos')
    async with request.app.state.session_factory() as session:
        run, challenge = await _case_run(session, run_id, user)
        if challenge.code == http_practice.FILES_CODE:
            _, expected = http_practice.case_for(run)
            correct = vm_logic.matches_answer(challenge.code, expected, payload)
            flag = http_practice.flag_for(run)
        else:
            _, expected = vm_logic.case_for(run, challenge.code)
            correct = vm_logic.matches_answer(challenge.code, expected, payload)
            flag = vm_logic.flag_for(run)
        return JSONResponse({'correct': correct, 'flag': flag if correct else None,
            'message': 'Investigación correcta. Registra los puntos para completar el reto.' if correct
            else 'Los resultados no coinciden. Revisa las fuentes y las relaciones del objetivo.'},
            headers={'Cache-Control': 'no-store'})
