"""Seguimiento, ranking, exportación y WebSocket."""

from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import Response
from sqlalchemy import func, select

from ..core import decode_token, get_current_user, require_roles
from ..models import Challenge, ChallengeCompletion, ChallengeGroupAssignment, ChallengeRun, GroupMembership, StudentGroup, Submission, User
from ..schemas import RankingResponse, RankingRow
from ..services.bootstrap import ranking_rows


router = APIRouter()

@router.get("/api/v1/reports/progress")
async def progress_report(request: Request, group_id: int | None = None, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        if group_id is not None:
            group = await session.get(StudentGroup, group_id)
            if group is None:
                raise HTTPException(status_code=404, detail="Grupo no encontrado")
            member_ids = list((await session.scalars(select(GroupMembership.user_id).where(GroupMembership.group_id == group_id))).all())
            challenge_ids = list((await session.scalars(select(ChallengeGroupAssignment.challenge_id).where(ChallengeGroupAssignment.group_id == group_id))).all())
        else:
            member_ids = list((await session.scalars(select(User.id).where(User.role == "player", User.is_active.is_(True)))).all())
            challenge_ids = list((await session.scalars(select(Challenge.id).where(Challenge.is_published.is_(True)))).all())
        if not member_ids or not challenge_ids:
            return []
        users = {u.id: u.username for u in (await session.scalars(select(User).where(User.id.in_(member_ids)))).all()}
        challenges = {c.id: c for c in (await session.scalars(select(Challenge).where(Challenge.id.in_(challenge_ids)))).all()}
        completions = {(c.user_id, c.challenge_id): c for c in (await session.scalars(select(ChallengeCompletion).where(ChallengeCompletion.user_id.in_(member_ids), ChallengeCompletion.challenge_id.in_(challenge_ids)))).all()}
        attempts_rows = (await session.execute(select(Submission.user_id, Submission.challenge_id, func.count(Submission.id)).where(Submission.user_id.in_(member_ids), Submission.challenge_id.in_(challenge_ids)).group_by(Submission.user_id, Submission.challenge_id))).all()
        attempts = {(int(u), int(c)): int(n) for u, c, n in attempts_rows}
        rows = []
        for uid in member_ids:
            for cid in challenge_ids:
                challenge = challenges.get(cid)
                if not challenge: continue
                completion = completions.get((uid, cid))
                rows.append({
                    "user_id": uid, "username": users.get(uid, ""), "challenge_code": challenge.code, "challenge_name": challenge.name,
                    "status": "Completado" if completion else "No iniciado", "points": int(completion.awarded_points) if completion else 0,
                    "attempts": attempts.get((uid, cid), 0), "completed_at": completion.completed_at.isoformat() if completion else None,
                })
        return rows


@router.get("/api/v1/ranking", response_model=RankingResponse)
async def ranking(request: Request, user=Depends(get_current_user)):
    return RankingResponse(rows=[RankingRow(**row) for row in await ranking_rows(request.app.state.session_factory)])


@router.get("/api/v1/reports/ranking.csv", response_class=Response)
async def export_ranking_csv(request: Request, _=Depends(require_roles("admin", "instructor"))):
    rows = await ranking_rows(request.app.state.session_factory)
    lines = ["position,username,total_points,challenges_completed"]
    for row in rows:
        # Los nombres de usuario no permiten comas al crearse, pero se protegen de todas formas para CSV.
        lines.append(f'{row["position"]},"{row["username"].replace(chr(34), chr(34) * 2)}",{row["total_points"]},{row["challenges_completed"]}')
    return Response("\n".join(lines) + "\n", media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ranking.csv"})


@router.get("/api/v1/progress")
async def progress(request: Request, user=Depends(require_roles("player"))):
    async with request.app.state.session_factory() as session:
        completed = (await session.scalars(select(ChallengeCompletion).where(ChallengeCompletion.user_id == user.id))).all()
        total = sum(item.awarded_points for item in completed)
        return {"total_points": total, "challenges_completed": len(completed)}


@router.websocket("/api/v1/ws/ranking")
async def ranking_socket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        if not token:
            raise ValueError("missing")
        decode_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.app.state.sockets.connect(websocket)
    await websocket.send_json({"type": "ranking.updated", "rows": await ranking_rows(websocket.app.state.session_factory)})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket.app.state.sockets.disconnect(websocket)


