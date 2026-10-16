"""Ejecución forense virtual: sin recursos SSH, archivos remotos ni secretos públicos."""
from fastapi import HTTPException
from ..core import now_utc, hash_password, submission_fingerprint
from ..models import ChallengeRun, ChallengeRunFlag
from ..domain.challenges.dfir import build_case
from .bootstrap import write_audit
from . import learning


def case_for(run):
    return build_case(submission_fingerprint(f"dfir:case:v1:{run.user_id}:{run.id}"))


def flag_for(run):
    return "FLAG{dfir-01_" + submission_fingerprint(f"dfir:flag:v1:{run.user_id}:{run.id}") + "}"


async def start(session, challenge, user, *, expires_at=None, policy=None):
    flags = [flag for flag in challenge.flags if flag.is_active]
    if len(flags) != 1 or flags[0].mode != "dynamic" or set(challenge.asset_references) not in ({"DFIR-CASE"}, {"DFIR-CASE", "LAB-KALI"}):
        raise HTTPException(409, "DFIR-01 requiere una flag dinámica activa y solo el expediente DFIR-CASE como activo.")
    if expires_at is None:
        expires_at, policy = await learning.plan_run(session, challenge, user)
    run = ChallengeRun(user_id=user.id, challenge_id=challenge.id, status="active",
                       expires_at=expires_at, workspace_strategy="dfir_case")
    session.add(run)
    await session.flush()
    value = flag_for(run)
    session.add(ChallengeRunFlag(run_id=run.id, flag_id=flags[0].id,
                                flag_hash=hash_password(value), fingerprint=submission_fingerprint(value)))
    await learning.lock_progress(session, run, challenge, create=True, policy=policy)
    await write_audit(session, user.id, "challenge_run.start", "challenge_run", str(run.id), {"challenge": challenge.code, "workspace_strategy": "dfir_case"})
    await session.commit()
    return run
