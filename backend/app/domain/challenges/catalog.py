"""Catálogo técnico del laboratorio.

Este archivo contiene únicamente valores de catálogo y seed para instalaciones
nuevas. No se usa como fuente de verdad de la base existente.
"""

DEMO_VM_IPS = {
    "Atacantes": {"10.10.20.10", "10.10.20.11", "10.10.20.12", "192.168.146.134"},
    "Víctimas": {"10.10.30.10", "10.10.30.11", "10.10.30.20", "10.10.30.21", "192.168.146.137"},
}

SEED_CHALLENGES = [
    {
        "code": "LAB-01",
        "name": "Reconocimiento SSH controlado",
        "description": "Identifica el servicio SSH de la máquina víctima del laboratorio y localiza la evidencia del ejercicio.",
        "instructions": (
            "Trabaja únicamente dentro del laboratorio autorizado. Desde la máquina atacante identifica "
            "el servicio SSH en 192.168.146.137, conéctate con las credenciales proporcionadas por el instructor "
            "y localiza /opt/ctf/flag.txt. No realices acciones fuera del entorno."
        ),
        "difficulty": "Básico",
        "category": "MISC",
        "scenario": "LAB-SSH-REAL",
        "mitre_technique": "T1046 — Network Service Scanning",
        "asset_references": ["LAB-LNXVICT", "LAB-VICTIMAS", "192.168.146.137"],
        "points": 100,
        "is_published": True,
        "flag_specs": [
            {
                "label": "Flag SSH dinámica",
                "mode": "dynamic",
                "template": "FLAG{lab-01_{{USER}}_{{RUN_ID}}_{{RAND}}}",
                "flag_order": 1,
                "is_active": True,
            }
        ],
    }
]
