"""Corridas descargables, sin reservar ni modificar máquinas del laboratorio."""
from fastapi import HTTPException
from ..core import now_utc, hash_password, submission_fingerprint
from ..models import ChallengeRun, ChallengeRunFlag
from ..domain.challenges.offline import CATALOG, build_case
from .bootstrap import write_audit
from . import learning


def case_for(run, code):
    return build_case(code, submission_fingerprint(f'offline:case:v1:{code}:{run.user_id}:{run.id}'))


def flag_for(run):
    return 'FLAG{offline_' + submission_fingerprint(f'offline:flag:v1:{run.challenge_id}:{run.user_id}:{run.id}') + '}'


async def start(session, challenge, user, *, expires_at=None, policy=None):
    flags = [flag for flag in challenge.flags if flag.is_active]
    if (challenge.code not in CATALOG or set(challenge.asset_references) not in ({'OFFLINE-CASE'}, {'OFFLINE-CASE', 'LAB-KALI'})
            or len(flags) != 1 or flags[0].mode != 'dynamic' or not flags[0].template):
        raise HTTPException(409, 'El ejercicio descargable necesita una flag dinámica activa y el activo OFFLINE-CASE.')
    if expires_at is None:
        expires_at, policy = await learning.plan_run(session, challenge, user)
    run = ChallengeRun(user_id=user.id, challenge_id=challenge.id, status='active',
                       expires_at=expires_at, workspace_strategy='offline_case')
    session.add(run)
    await session.flush()
    value = flag_for(run)
    session.add(ChallengeRunFlag(run_id=run.id, flag_id=flags[0].id, flag_hash=hash_password(value), fingerprint=submission_fingerprint(value)))
    await learning.lock_progress(session, run, challenge, create=True, policy=policy)
    await write_audit(session, user.id, 'challenge_run.start', 'challenge_run', str(run.id), {'challenge': challenge.code, 'workspace_strategy': 'offline_case'})
    await session.commit()
    return run
