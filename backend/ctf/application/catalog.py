"""Descripción del catálogo nuevo; guardarlo es una operación explícita de consola."""
from ..domain.laboratory import SCENARIOS, POINTS, INSTRUCTIONS

NAMES = {
    "ESC-01-RECON": "Reconocimiento de servicios",
    "ESC-02-BRUTEFORCE": "Acceso SSH de práctica",
    "ESC-03-WEBEXPLOIT": "Investigación SQL en DVWA",
    "ESC-04-LATERAL": "Movimiento lateral Windows A → B",
    "ESC-05-EXFIL": "Transferencia controlada desde Samba",
}


def drafts():
    return [{"code": s.code, "name": NAMES[s.code], "strategy": s.strategy, "difficulty": s.difficulty,
             "points": POINTS[s.difficulty], "mitre": s.mitre, "victim": s.victims[0], "instructions": INSTRUCTIONS[s.strategy],
             "implementation_available": s.enabled} for s in SCENARIOS]
