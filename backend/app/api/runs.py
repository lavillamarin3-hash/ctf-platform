"""Ciclo de ejecución, cierre y validación de retos."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..core import get_current_user, now_utc, require_roles, submission_fingerprint
from ..models import Challenge, ChallengeCompletion, ChallengeRun, ChallengeRunFlag, Submission, User
from ..schemas import RunView, SubmissionRequest, SubmissionResponse
from ..services.bootstrap import ranking_rows, write_audit
from ..services.challenge_runtime import (
    _asset_ref_key, _find_challenge_vm, _sync_player_guacamole_permissions,
    render_dynamic_flag,
)


from fastapi import APIRouter

router = APIRouter()

async def start_challenge(code: str, request: Request, user=Depends(require_roles("player"))):
    await check_rate_limit(request.app.state.redis, f"rate:start:{user.id}:{code}", maximum=6)
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == code, Challenge.is_published.is_(True)))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no disponible")

        assigned = await session.scalar(
            select(ChallengeGroupAssignment.id).join(
                GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id
            ).join(
                StudentGroup, StudentGroup.id == GroupMembership.group_id
            ).where(
                ChallengeGroupAssignment.challenge_id == challenge.id,
                GroupMembership.user_id == user.id,
                StudentGroup.is_active.is_(True),
            )
        )
        if assigned is None:
            raise HTTPException(status_code=403, detail="Este reto no está asignado a tu grupo")

        expires_at = now_utc() + timedelta(minutes=90)
        run = ChallengeRun(user_id=user.id, challenge_id=challenge.id, status="active", expires_at=expires_at, workspace_strategy="shared_lab_vm")
        session.add(run)
        await session.flush()

        target_lab, target_vm = await _find_challenge_vm(session, challenge)
        target_url: str
        target_protocol = None
        laboratory_code = target_lab.code if target_lab else None

        if target_vm and target_vm.guacamole_connection_id:
            try:
                # Reutilizamos una conexión real ya administrada por Guacamole; no creamos una conexión por cada ejecución.
                target_url = await request.app.state.guacamole.direct_connection_url(target_vm.guacamole_connection_id)
                connections = await request.app.state.guacamole_admin.list_connections()
                connection = next((item for item in connections if item.identifier == target_vm.guacamole_connection_id), None)
                target_protocol = connection.protocol if connection else None
                external_reference = f"vm:{target_vm.id}:connection:{target_vm.guacamole_connection_id}:run:{run.id}"
            except RuntimeError as exc:
                run.status = "provisioning_failed"
                await session.commit()
                raise HTTPException(status_code=503, detail=str(exc)) from exc
        else:
            try:
                # Compatibilidad para retos sin VM asociada.
                remote = await request.app.state.guacamole.provision(user.username, challenge.code, run.id)
                target_url = remote.launch_url
                external_reference = remote.external_reference
            except RuntimeError as exc:
                run.status = "provisioning_failed"
                await session.commit()
                raise HTTPException(status_code=503, detail=str(exc)) from exc

        assignment = RemoteAccessAssignment(
            run_id=run.id,
            external_reference=external_reference,
            launch_url=target_url,
            expires_at=expires_at,
        )
        session.add(assignment)

        for flag in challenge.flags:
            if flag.is_active and flag.mode == "dynamic" and flag.template:
                clear_value = render_dynamic_flag(flag.template, code=challenge.code, username=user.username, run_id=run.id)
                session.add(ChallengeRunFlag(run_id=run.id, flag_id=flag.id, flag_hash=hash_password(clear_value), fingerprint=submission_fingerprint(clear_value)))

        await write_audit(session, user.id, "challenge_run.start", "challenge_run", str(run.id), {
            "challenge": code,
            "remote_reference": external_reference,
            "target_vm": target_vm.name if target_vm else None,
            "target_laboratory": target_lab.code if target_lab else None,
        })
        await session.commit()

        return RunView(
            id=run.id,
            challenge_code=challenge.code,
            status=run.status,
            started_at=run.started_at,
            expires_at=expires_at,
            launch_url=target_url,
            connection_state="ready",
            workspace_strategy=run.workspace_strategy,
            target_vm_name=target_vm.name if target_vm else None,
            target_vm_ip=target_vm.ip_address if target_vm else None,
            target_protocol=target_protocol,
            laboratory_code=laboratory_code,
        )


@router.get("/api/v1/runs", response_model=list[RunView])
async def list_runs(request: Request, user=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        statement = select(ChallengeRun, Challenge.code, RemoteAccessAssignment).join(Challenge, Challenge.id == ChallengeRun.challenge_id).outerjoin(RemoteAccessAssignment, RemoteAccessAssignment.run_id == ChallengeRun.id)
        if user.role == "player":
            statement = statement.where(ChallengeRun.user_id == user.id)
        elif user.role not in ("admin", "instructor"):
            return []
        statement = statement.order_by(ChallengeRun.started_at.desc()).limit(30)
        rows = (await session.execute(statement)).all()
        current = now_utc()
        response: list[RunView] = []
        for run, code, assignment in rows:
            state = "expired" if run.status == "active" and run.expires_at < current else run.status
            response.append(RunView(id=run.id, challenge_code=code, status=state, started_at=run.started_at, expires_at=run.expires_at, launch_url=assignment.launch_url if assignment and user.role == "player" else None, connection_state=assignment.status if assignment else None, workspace_strategy=run.workspace_strategy))
        return response


@router.post("/api/v1/runs/{run_id}/close", response_model=RunView)
async def close_run(run_id: int, request: Request, user=Depends(require_roles("player"))):
    async with request.app.state.session_factory() as session:
        run = await session.scalar(select(ChallengeRun).options(selectinload(ChallengeRun.assignment)).where(ChallengeRun.id == run_id, ChallengeRun.user_id == user.id))
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        if run.status == "active" and run.assignment:
            try:
                await request.app.state.guacamole.revoke(run.assignment.external_reference)
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            run.assignment.status = "revoked"
            run.status = "closed"
            run.closed_at = now_utc()
            await write_audit(session, user.id, "challenge_run.close", "challenge_run", str(run.id))
            await session.commit()
        return RunView(id=run.id, challenge_code="", status=run.status, started_at=run.started_at, expires_at=run.expires_at, launch_url=None, connection_state=run.assignment.status if run.assignment else None, workspace_strategy=run.workspace_strategy)


@router.post("/api/v1/challenges/{code}/submissions", response_model=SubmissionResponse)
async def submit_flag(code: str, payload: SubmissionRequest, request: Request, user=Depends(require_roles("player"))):
    await check_rate_limit(request.app.state.redis, f"rate:flag:{user.id}:{code}", maximum=8)
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == code, Challenge.is_published.is_(True)))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no disponible")
        assigned = await session.scalar(
            select(ChallengeGroupAssignment.id).join(
                GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id
            ).join(
                StudentGroup, StudentGroup.id == GroupMembership.group_id
            ).where(
                ChallengeGroupAssignment.challenge_id == challenge.id,
                GroupMembership.user_id == user.id,
                StudentGroup.is_active.is_(True),
            )
        )
        if assigned is None:
            raise HTTPException(status_code=403, detail="Este reto no está asignado a tu grupo")
        flags = [item for item in challenge.flags if item.is_active]
        if not flags:
            raise HTTPException(status_code=409, detail="El reto todavía no está configurado con flags activas")
        run = await session.scalar(select(ChallengeRun).where(ChallengeRun.user_id == user.id, ChallengeRun.challenge_id == challenge.id, ChallengeRun.status == "active").order_by(ChallengeRun.id.desc()))
        if run is None or run.expires_at < now_utc():
            raise HTTPException(status_code=409, detail="Debes iniciar el reto antes de enviar la flag")
        matched = None
        for flag in flags:
            if flag.mode == "dynamic":
                if run is None:
                    continue
                run_flag = await session.scalar(select(ChallengeRunFlag).where(ChallengeRunFlag.run_id == run.id, ChallengeRunFlag.flag_id == flag.id))
                if run_flag and verify_password(payload.value, run_flag.flag_hash):
                    matched = flag
                    break
            elif flag.flag_hash and verify_password(payload.value, flag.flag_hash):
                matched = flag
                break
        submission = Submission(user_id=user.id, challenge_id=challenge.id, flag_id=matched.id if matched else None, submitted_value_hmac=submission_fingerprint(payload.value), is_correct=matched is not None)
        session.add(submission)
        awarded_points, complete = 0, False
        if matched:
            correct_ids = set((await session.scalars(select(Submission.flag_id).where(Submission.user_id == user.id, Submission.challenge_id == challenge.id, Submission.is_correct.is_(True)))).all())
            correct_ids.add(matched.id)
            if {item.id for item in flags}.issubset(correct_ids):
                completion = await session.scalar(select(ChallengeCompletion).where(ChallengeCompletion.user_id == user.id, ChallengeCompletion.challenge_id == challenge.id))
                if completion is None:
                    completion = ChallengeCompletion(user_id=user.id, challenge_id=challenge.id, awarded_points=challenge.points)
                    session.add(completion)
                    awarded_points, complete = challenge.points, True
                    await write_audit(session, user.id, "challenge.complete", "challenge", str(challenge.id), {"code": code, "points": challenge.points})
        await session.commit()
    if complete:
        rows = await ranking_rows(request.app.state.session_factory)
        payload_event = {"type": "ranking.updated", "rows": rows}
        await request.app.state.sockets.broadcast(payload_event)
        try:
            await request.app.state.redis.publish("ctf:ranking", __import__("json").dumps(payload_event))
        except Exception:
            pass
        return SubmissionResponse(correct=True, challenge_completed=True, awarded_points=awarded_points, message="Reto completado. El ranking se actualizó.")
    if matched:
        return SubmissionResponse(correct=True, challenge_completed=False, awarded_points=0, message="Flag correcta. Continúa con las flags restantes.")
    return SubmissionResponse(correct=False, challenge_completed=False, awarded_points=0, message="Flag incorrecta. Revisa el escenario e inténtalo de nuevo.")


