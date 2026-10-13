"""Caso sintético reproducible. La semilla privada nunca se entrega al alumno."""
from datetime import datetime, timedelta, timezone
import hashlib
import random

CODE = "DFIR-01"


def build_case(seed: str) -> tuple[dict, dict]:
    rng = random.Random(seed)
    base = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc) + timedelta(minutes=rng.randrange(600))
    auth_skew, http_skew = rng.choice([73, 119, 181]), -rng.choice([41, 89, 127])
    auth, http, network = [], [], []
    culprit = rng.randrange(12)
    answer = {}
    for index in range(12):
        session = f"s-{rng.getrandbits(64):016x}"
        user = f"analista{rng.randrange(100, 999)}"
        ip = f"10.77.0.{index + 20}"
        start = base + timedelta(seconds=index * 23)
        token = f"r-{rng.getrandbits(64):016x}"
        # Cada candidato comparte dos señales con el incidente; solo uno las reúne todas.
        suspicious = index == culprit
        mfa = "bypassed" if suspicious or index % 3 == 0 else "verified"
        destination = "203.0.113.77" if suspicious or index % 3 == 1 else "192.0.2.10"
        size = rng.randrange(800000, 950000) if suspicious or index % 3 == 2 else rng.randrange(1000, 4000)
        auth.append({"time": (start + timedelta(seconds=auth_skew)).isoformat(), "session": session, "user": user, "source": ip, "result": "success", "mfa": mfa})
        # Intentos fallidos y operaciones legítimas evitan resolver por volumen o por IP solamente.
        auth.append({"time": (start - timedelta(seconds=8) + timedelta(seconds=auth_skew)).isoformat(), "session": "-", "user": user, "source": ip, "result": "failed", "mfa": "denied"})
        http.append({"time": (start + timedelta(seconds=12 + http_skew)).isoformat(), "session": session, "request": token, "path": "/reports/export", "status": 200, "bytes": size})
        network.append({"time": (start + timedelta(seconds=15)).isoformat(), "request": token, "source": "10.77.1.8", "destination": destination, "bytes": size})
        if suspicious:
            answer = {"session": session, "user": user, "request": token, "destination": destination, "auth_utc": start.isoformat()}
    for rows in (auth, http, network):
        rng.shuffle(rows)
    calibration = []
    for offset in (0, 300):
        reference = base - timedelta(seconds=600 - offset)
        calibration.append({"reference_utc": reference.isoformat(), "auth_clock": (reference + timedelta(seconds=auth_skew)).isoformat(), "http_clock": (reference + timedelta(seconds=http_skew)).isoformat()})
    files = {"auth.json": auth, "http.json": http, "network.json": network}
    import json
    contents = {name: json.dumps(rows, ensure_ascii=False, indent=2) for name, rows in files.items()}
    bundle = {
        "title": "DFIR-01 · La exportación fuera de ventana",
        "brief": "Reconstruye la única sesión con MFA omitido, exportación HTTP exitosa superior a 500000 bytes y transferencia correlacionada a 203.0.113.77 en menos de 60 segundos desde la autenticación. Une session y request; una IP o un volumen aislado no bastan. Entrega la hora real UTC de autenticación. Todos los datos son sintéticos.",
        "clock_notes": "Red usa UTC exacto. Auth y HTTP tienen un desfase constante, incluso si su texto indica +00:00. Calcúlalo con las dos balizas de calibración.",
        "calibration": calibration,
        "files": contents,
        "sha256": {name: hashlib.sha256(data.encode()).hexdigest() for name, data in contents.items()},
    }
    return bundle, answer


def matches_answer(expected: dict, supplied: dict) -> bool:
    try:
        instant = datetime.fromisoformat(supplied.get("auth_utc", "").strip().replace("Z", "+00:00"))
        if instant.tzinfo is None or instant != datetime.fromisoformat(expected["auth_utc"]):
            return False
        return all(supplied.get(key, "").strip() == expected[key] for key in ("session", "user", "request", "destination"))
    except (ValueError, TypeError):
        return False
