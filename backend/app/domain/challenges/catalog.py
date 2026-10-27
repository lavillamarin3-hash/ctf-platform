"""Catálogo técnico del laboratorio.

Este archivo contiene únicamente valores de catálogo y seed para instalaciones
nuevas. No se usa como fuente de verdad de la base existente.
"""

DEMO_VM_IPS = {
    "Atacantes": {"10.10.20.10", "10.10.20.11", "10.10.20.12"},
    "Víctimas": {"10.10.30.10", "10.10.30.11", "10.10.30.12", "10.10.30.20", "10.10.30.21"},
}

OPERATIONAL_VM_TARGETS = {
    "LAB-KALI": "10.10.20.10", "LAB-KALI-PURPLE": "10.10.20.11",
    "LAB-KALI-BLUE": "10.10.20.12", "LAB-WINVICT-A": "10.10.30.10",
    "LAB-WINVICT-B": "10.10.30.11", "LAB-LNXVICT": "10.10.30.12",
    "LAB-SRVWEB": "10.10.30.20", "LAB-SRVFSAD": "10.10.30.21",
}

SEED_CHALLENGES = [
    {
        "code": "LAB-01",
        "name": "Reconocimiento SSH controlado",
        "description": "Identifica el servicio SSH de la máquina víctima del laboratorio y localiza la evidencia del ejercicio.",
        "instructions": (
            "Trabaja únicamente dentro del laboratorio autorizado. Desde la máquina atacante identifica "
            "el servicio SSH en 10.10.30.12, conéctate con las credenciales proporcionadas por el instructor "
            "y localiza /opt/ctf/flag.txt. No realices acciones fuera del entorno."
        ),
        "difficulty": "Básico",
        "category": "MISC",
        "scenario": "LAB-SSH-REAL",
        "mitre_technique": "T1046 — Network Service Scanning",
        "asset_references": ["LAB-LNXVICT", "LAB-VICTIMAS", "10.10.30.12"],
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
    },
    {
        # Borrador: no publicar hasta verificar acceso Kali, servicio didáctico,
        # inyección dinámica y limpieza física en las dos VMs reales.
        "code": "ESC-01-RECON",
        "name": "Descubre el servicio de evidencia",
        "description": "Desde Kali identifica un servicio de práctica en la VM Linux víctima y recupera su evidencia dinámica.",
        "instructions": (
            "Desde la conexión Kali atacante (10.10.20.10), examina únicamente el servicio "
            "didáctico de 10.10.30.12 en el puerto 18081. Escanea solo 22 y 18081 y solicita "
            "http://10.10.30.12:18081/evidence. Copia la evidencia dinámica, envíala y cierra "
            "el laboratorio. El instructor debe verificar el servicio antes de publicar."
        ),
        "difficulty": "Básico",
        "category": "MISC",
        "scenario": "ESC-01-RECON",
        "mitre_technique": "T1046 — Network Service Scanning",
        "asset_references": ["LAB-LNXVICT", "LAB-KALI"],
        "points": 100,
        "is_published": False,
        "flag_specs": [
            {
                "label": "Evidencia dinámica de reconocimiento",
                "mode": "dynamic",
                "template": "FLAG{esc-01_{{USER}}_{{RUN_ID}}_{{RAND}}}",
                "flag_order": 1,
                "is_active": True,
            }
        ],
    },
]

DFIR_DRAFT = {
    "code": "DFIR-01", "name": "Correlación forense de incidente",
    "description": "Reconstruye una exportación sospechosa cruzando autenticación, HTTP y red con desfases horarios y falsos positivos.",
    "instructions": "Inicia el caso y prepara las tres fuentes sintéticas en la terminal de Kali. Verifica sus SHA-256, calcula los desfases con las balizas y correlaciona session/request para identificar la única secuencia que cumple todos los indicadores del expediente. Entrega sesión, usuario, solicitud, destino y hora UTC de autenticación. Valida el análisis, copia o envía la flag y cierra el caso. Utiliza las herramientas de Kali y las pistas del reto para analizar los JSON.",
    "difficulty": "Avanzado", "category": "FORENSICS", "scenario": "DFIR-01",
    "mitre_technique": "T1078 — Valid Accounts (análisis de evidencias)",
    "asset_references": ["DFIR-CASE"], "points": 500, "is_published": False,
    "flag_specs": [{"label": "Evidencia forense dinámica", "mode": "dynamic", "template": "FLAG{dfir-01_{{RAND}}}", "flag_order": 1, "is_active": True}],
}
SEED_CHALLENGES.append(DFIR_DRAFT)
