"""Resolución de flags efectivas sin modificar el esquema ni los datos existentes."""

from __future__ import annotations

from ..domain.challenges.catalog import SEED_CHALLENGES
from ..models import ChallengeFlag


_OVERRIDES: dict[str, dict[int, dict[str, str]]] = {}
for challenge in SEED_CHALLENGES:
    specs: dict[int, dict[str, str]] = {}
    for spec in challenge.get("flag_specs", []):
        if spec.get("mode") == "dynamic" and spec.get("template"):
            specs[int(spec["flag_order"])] = {
                "mode": "dynamic",
                "template": str(spec["template"]),
            }
    if specs:
        _OVERRIDES[str(challenge["code"])] = specs


def effective_mode_template(challenge_code: str, flag: ChallengeFlag) -> tuple[str, str | None]:
    """Resuelve modo/plantilla sin persistir cambios en PostgreSQL."""
    if flag.mode == "dynamic" and flag.template:
        return "dynamic", flag.template
    override = _OVERRIDES.get(challenge_code, {}).get(int(flag.flag_order))
    if flag.is_active and override:
        return override["mode"], override["template"]
    return flag.mode, flag.template


def is_effectively_dynamic(challenge_code: str, flag: ChallengeFlag) -> bool:
    mode, template = effective_mode_template(challenge_code, flag)
    return bool(flag.is_active and mode == "dynamic" and template)
