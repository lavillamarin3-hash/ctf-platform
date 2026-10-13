"""Ejecución forense virtual: sin recursos SSH, archivos remotos ni secretos públicos."""
from datetime import timedelta
from fastapi import HTTPException
from ..core import now_utc, hash_password, submission_fingerprint
from ..models import ChallengeRun, ChallengeRunFlag
from ..domain.challenges.dfir import build_case
from .bootstrap import write_audit


def case_for(run):
    return build_case(submission_fingerprint(f"dfir:case:v1:{run.user_id}:{run.id}"))


def flag_for(run):
    return "FLAG{dfir-01_" + submission_fingerprint(f"dfir:flag:v1:{run.user_id}:{run.id}") + "}"


async def start(session, challenge, user):
    flags = [flag for flag in challenge.flags if flag.is_active]
    if len(flags) != 1 or flags[0].mode != "dynamic" or challenge.asset_references != ["DFIR-CASE"]:
        raise HTTPException(409, "DFIR-01 requiere una flag dinámica activa y solo el expediente DFIR-CASE como activo.")
    run = ChallengeRun(user_id=user.id, challenge_id=challenge.id, status="active",
                       expires_at=now_utc() + timedelta(hours=2), workspace_strategy="dfir_case")
    session.add(run)
    await session.flush()
    value = flag_for(run)
    session.add(ChallengeRunFlag(run_id=run.id, flag_id=flags[0].id,
                                flag_hash=hash_password(value), fingerprint=submission_fingerprint(value)))
    await write_audit(session, user.id, "challenge_run.start", "challenge_run", str(run.id), {"challenge": challenge.code, "workspace_strategy": "dfir_case"})
    await session.commit()
    return run
