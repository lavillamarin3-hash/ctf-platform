from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .core import (
    create_token,
    decode_token,
    get_current_user,
    get_settings,
    hash_password,
    now_utc,
    require_roles,
    submission_fingerprint,
    verify_password,
)
from .db import create_schema, make_session_factory
from .guacamole import GuacamoleApiError, make_guacamole_adapter, make_guacamole_admin
from .models import AuditEvent, Challenge, ChallengeCompletion, ChallengeFlag, ChallengeRun, ChallengeRunFlag, Laboratory, RemoteAccessAssignment, Role, Submission, User, VMAsset, StudentGroup, GroupMembership, ChallengeGroupAssignment
from .schemas import (
    ChallengeCreate,
    ChallengeView,
    FlagCreate,
    FlagUpdate,
    LoginRequest,
    RankingResponse,
    RankingRow,
    RunView,
    SubmissionRequest,
    SubmissionResponse,
    TokenResponse,
    UserCreate,
    UserUpdate,
    UserView,
    ProfileUpdate,
    PasswordChange,
    LaboratoryCreate,
    LaboratoryView,
    VMCreate,
    VMView,
    GroupCreate,
    GroupView,
    GroupMemberAdd,
    ChallengeGroupAssignmentRequest,
    GuacamoleStatus,
    GuacamoleUserCreate,
    GuacamoleUserUpdate,
    GuacamoleUserView,
    GuacamoleConnectionCreate,
    GuacamoleConnectionUpdate,
    GuacamoleConnectionView,
    GuacamolePermissionSet,
    GuacamolePermissionPatch,
)


SEED_CHALLENGES = (
    {"code":"WEB-01","name":"Robots secreto","category":"WEB","scenario":"ESC-01-RECON","description":"Encuentra una ruta que no aparece en la navegación pública del servidor.","instructions":"Revisa la información pública del servicio y localiza el recurso oculto del ejercicio.","difficulty":"Básico","mitre_technique":"T1046 — Network Service Scanning","asset_references":["LAB-SRVWEB"],"points":100,"flag_values":["FLAG{web_robots_demo}"]},
    {"code":"WEB-02","name":"Login vulnerable","category":"WEB","scenario":"ESC-03-WEBEXPLOIT","description":"Analiza el formulario de autenticación y consigue acceso al usuario de laboratorio.","instructions":"Trabaja exclusivamente contra LAB-SRVWEB. Identifica el comportamiento inseguro del formulario.","difficulty":"Básico","mitre_technique":"T1190 — Exploit Public-Facing Application","asset_references":["LAB-SRVWEB"],"points":100,"flag_values":["FLAG{web_login_demo}"]},
    {"code":"WEB-03","name":"SQL Injection","category":"WEB","scenario":"ESC-03-WEBEXPLOIT","description":"Obtén el dato solicitado desde la aplicación vulnerable mediante una consulta manipulada.","instructions":"Documenta el comportamiento de la entrada y recupera la primera flag del ejercicio.","difficulty":"Medio","mitre_technique":"T1190 — Exploit Public-Facing Application","asset_references":["LAB-SRVWEB"],"points":250,"flag_values":["FLAG{web_sqli_demo}"]},
    {"code":"WEB-04","name":"File Upload controlado","category":"WEB","scenario":"ESC-03-WEBEXPLOIT","description":"Investiga una función de carga de archivos con validación insuficiente.","instructions":"Utiliza únicamente archivos preparados para el laboratorio y encuentra el recurso de prueba.","difficulty":"Avanzado","mitre_technique":"T1190 — Exploit Public-Facing Application","asset_references":["LAB-SRVWEB"],"points":500,"flag_values":["FLAG{web_upload_demo}"]},
    {"code":"CRY-01","name":"Base64 no es cifrado","category":"CRIPTOGRAFÍA","scenario":None,"description":"Identifica la codificación utilizada y recupera el mensaje original.","instructions":"Analiza el texto entregado y determina la transformación aplicada.","difficulty":"Básico","mitre_technique":"—","asset_references":["Archivo de reto"],"points":100,"flag_values":["FLAG{crypto_b64_demo}"]},
    {"code":"CRY-02","name":"XOR de una clave","category":"CRIPTOGRAFÍA","scenario":None,"description":"Recupera el texto original a partir de una operación XOR con una clave sencilla.","instructions":"Puedes automatizar el análisis con Python o CyberChef.","difficulty":"Medio","mitre_technique":"—","asset_references":["Archivo de reto"],"points":250,"flag_values":["FLAG{crypto_xor_demo}"]},
    {"code":"CRY-03","name":"RSA débil","category":"CRIPTOGRAFÍA","scenario":None,"description":"Analiza una configuración criptográfica débil y recupera el mensaje.","instructions":"Identifica qué propiedad de la configuración permite resolver el reto.","difficulty":"Avanzado","mitre_technique":"—","asset_references":["Archivo de reto"],"points":500,"flag_values":["FLAG{crypto_rsa_demo}"]},
    {"code":"FOR-01","name":"Metadatos reveladores","category":"FORENSE","scenario":"ESC-01-RECON","description":"Examina una evidencia y localiza información almacenada en sus metadatos.","instructions":"Analiza la evidencia con herramientas de inspección de archivos.","difficulty":"Básico","mitre_technique":"T1046 — Network Service Scanning","asset_references":["Evidencia digital"],"points":100,"flag_values":["FLAG{forensic_meta_demo}"]},
    {"code":"FOR-02","name":"PCAP bajo la lupa","category":"FORENSE","scenario":"ESC-05-EXFIL","description":"Analiza una captura de tráfico para reconstruir la comunicación relevante.","instructions":"Localiza la comunicación asociada con la actividad del escenario y extrae la evidencia.","difficulty":"Medio","mitre_technique":"T1048 — Exfiltration Over Alternative Protocol","asset_references":["PCAP de laboratorio"],"points":250,"flag_values":["FLAG{forensic_pcap_demo}"]},
    {"code":"FOR-03","name":"Memoria del sistema","category":"FORENSE","scenario":"ESC-02-BRUTEFORCE","description":"Investiga una imagen de memoria para encontrar procesos y artefactos del ejercicio.","instructions":"Analiza la memoria proporcionada con una herramienta forense adecuada.","difficulty":"Avanzado","mitre_technique":"T1110.001 — Password Guessing","asset_references":["Dump de memoria"],"points":500,"flag_values":["FLAG{forensic_mem_demo}"]},
    {"code":"REV-01","name":"Strings ocultos","category":"REVERSING","scenario":None,"description":"Inspecciona un binario y encuentra información expuesta en sus cadenas.","instructions":"Comienza con un análisis superficial antes de usar un descompilador.","difficulty":"Básico","mitre_technique":"—","asset_references":["Binario ELF"],"points":100,"flag_values":["FLAG{rev_strings_demo}"]},
    {"code":"REV-02","name":"Validador de contraseña","category":"REVERSING","scenario":None,"description":"Analiza cómo el binario comprueba una contraseña y recupera la lógica de validación.","instructions":"Utiliza Ghidra u otra herramienta de reversing.","difficulty":"Medio","mitre_technique":"—","asset_references":["Binario ELF"],"points":250,"flag_values":["FLAG{rev_password_demo}"]},
    {"code":"PWN-01","name":"Ret2Win","category":"PWN / EXPLOITING","scenario":"ESC-04-LATERAL","description":"Controla el flujo de ejecución de un servicio vulnerable de laboratorio.","instructions":"El objetivo es alcanzar la función de éxito del binario dentro del entorno autorizado.","difficulty":"Avanzado","mitre_technique":"T1021.002 — SMB/Windows Admin Shares","asset_references":["LAB-LNXVICT"],"points":500,"flag_values":["FLAG{pwn_ret2win_demo}"]},
    {"code":"OSI-01","name":"Dominio y DNS","category":"OSINT","scenario":"ESC-01-RECON","description":"Correlaciona información de dominio y DNS para descubrir una pista del escenario.","instructions":"Utiliza únicamente las fuentes ficticias proporcionadas por el reto.","difficulty":"Básico","mitre_technique":"T1046 — Network Service Scanning","asset_references":["Fuentes del reto"],"points":100,"flag_values":["FLAG{osint_dns_demo}"]},
    {"code":"STE-01","name":"Imagen con mensaje oculto","category":"ESTEGANOGRAFÍA","scenario":None,"description":"Extrae información escondida dentro de una imagen de laboratorio.","instructions":"Analiza metadatos, estructura del archivo y canales ocultos antes de concluir.","difficulty":"Medio","mitre_technique":"—","asset_references":["imagen.png"],"points":250,"flag_values":["FLAG{stego_image_demo}"]},
    {"code":"MISC-01","name":"Script de automatización","category":"MISC","scenario":None,"description":"Automatiza una tarea repetitiva para transformar el contenido del reto.","instructions":"Escribe un pequeño script y valida que el resultado sea reproducible.","difficulty":"Medio","mitre_technique":"—","asset_references":["Archivo de reto"],"points":250,"flag_values":["FLAG{misc_script_demo}"]},
    {"code":"LAB-01","name":"Reconocimiento SSH controlado","category":"MISC","scenario":"ESC-01-RECON","description":"Identifica el servicio SSH de una máquina víctima preparada para el laboratorio y localiza la evidencia del ejercicio.","instructions":"Usa únicamente la VM LAB-LNXVICT del entorno autorizado. Desde tu máquina atacante identifica el servicio SSH, conéctate con las credenciales entregadas por el instructor y localiza el archivo /opt/ctf/flag.txt. No realices acciones fuera de la red del laboratorio.","difficulty":"Básico","mitre_technique":"T1046 — Network Service Scanning","asset_references":["LAB-LNXVICT"],"points":100,"flag_values":["FLAG{ssh_lab_demo}"]},
)


# Inventario de demostración actualmente disponible. La interfaz también lo usa como catálogo.
DEMO_VM_IPS = {
    "Atacantes": {"192.168.146.134"},
    "Víctimas": {"192.168.164.137"},
}


def vm_view(item: VMAsset, *, guacamole_url: str | None = None, guacamole_protocol: str | None = None) -> VMView:
    return VMView(
        id=item.id, laboratory_id=item.laboratory_id, name=item.name, os=item.os, ip_address=item.ip_address,
        vlan=item.vlan, role=item.role, network_role=item.network_role, subnet=item.subnet, profile=item.profile,
        baseline=item.baseline, nutanix_vm_id=item.nutanix_vm_id, guacamole_connection_id=item.guacamole_connection_id,
        guacamole_url=guacamole_url, guacamole_protocol=guacamole_protocol, status=item.status
    )

def laboratory_view(item: Laboratory) -> LaboratoryView:
    return LaboratoryView(
        id=item.id, code=item.code, name=item.name, description=item.description, segment=item.segment, status=item.status,
        vms=[vm_view(vm) for vm in item.vms]
    )

class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        for websocket in list(self.connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket)


async def write_audit(session, actor_id: int | None, action: str, entity_type: str, entity_id: str, details: dict | None = None) -> None:
    session.add(AuditEvent(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))


async def seed_data(session_factory) -> None:
    settings = get_settings()
    async with session_factory() as session:
        roles = {
            "admin": "Administración completa de la plataforma",
            "instructor": "Diseño y seguimiento de retos",
            "player": "Participante de retos",
            "guest": "Consulta de solo lectura",
        }
        for name, description in roles.items():
            if not await session.scalar(select(Role).where(Role.name == name)):
                session.add(Role(name=name, description=description))

        # Desde esta fase no se crean cuentas ficticias automáticamente.
        # Los usuarios reales se crean desde Administración > Gestionar usuarios y,
        # por defecto, se sincronizan con Guacamole.

        await session.flush()

        # El inventario/retos de demostración solo se conserva para instalaciones
        # que ya lo tengan; no se presentan como usuarios ficticios en la interfaz.
        if not settings.ctf_seed_demo_data:
            await session.commit()
            return

        inventory = [
            {"code": "LAB-ATACANTES", "name": "Laboratorio de Atacantes", "segment": "VLAN 20 · 10.10.20.0/24", "vms": [
                ("LAB-KALI", "Kali Linux 2026.2", "10.10.20.10", "Atacantes", "VLAN 20", "10.10.20.0/24", "standard"),
                ("LAB-KALI-PURPLE", "Kali Linux Purple 2026.2", "10.10.20.11", "Atacantes", "VLAN 20", "10.10.20.0/24", "standard"),
                ("LAB-KALI-BLUE", "Linux Mint", "10.10.20.12", "Atacantes", "VLAN 20", "10.10.20.0/24", "standard"),
            ]},
            {"code": "LAB-VICTIMAS", "name": "Laboratorio de Víctimas", "segment": "VLAN 30 · 10.10.30.0/24", "vms": [
                ("LAB-WINVICT-A", "Windows 10 (ES)", "10.10.30.10", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-WINVICT-B", "Windows 10 (ES)", "10.10.30.11", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-LNXVICT", "Ubuntu Server 26.04", "10.10.30.12", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-SRVWEB", "Ubuntu Server 26.04", "10.10.30.20", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
                ("LAB-SRVFSAD", "Ubuntu Server 26.04", "10.10.30.21", "Víctimas", "VLAN 30", "10.10.30.0/24", "vulnerable"),
            ]},
        ]
        for lab_data in inventory:
            lab = await session.scalar(select(Laboratory).where(Laboratory.code == lab_data["code"]))
            if lab is None:
                lab = Laboratory(code=lab_data["code"], name=lab_data["name"], description=f"{lab_data['segment']} · Cyber range", segment=lab_data["segment"], status="ready")
                session.add(lab)
                await session.flush()
            for vm_name, os_name, ip, net_role, vlan, subnet, profile in lab_data["vms"]:
                vm = await session.scalar(select(VMAsset).where(VMAsset.name == vm_name))
                if vm is None:
                    session.add(VMAsset(laboratory_id=lab.id, name=vm_name, os=os_name, ip_address=ip, vlan=vlan, role=net_role, network_role=net_role, subnet=subnet, profile=profile, status="ready"))

        await session.flush()
        for item in SEED_CHALLENGES:
            challenge = await session.scalar(select(Challenge).where(Challenge.code == item["code"]))
            if challenge is None:
                flag_values = item.get("flag_values", [])
                challenge_data = {key: value for key, value in item.items() if key not in {"flag_values"}}
                challenge = Challenge(**challenge_data)
                session.add(challenge)
                await session.flush()
                for order, flag_value in enumerate(flag_values, start=1):
                    session.add(ChallengeFlag(challenge_id=challenge.id, label=f"Flag {order}", flag_hash=hash_password(flag_value), flag_order=order, is_active=True))
            else:
                # Completa campos nuevos en instalaciones que ya tenían los retos anteriores.
                changed = False
                for key in ("category", "scenario"):
                    value = item.get(key)
                    if getattr(challenge, key, None) != value and (getattr(challenge, key, None) in (None, "", "MISC")):
                        setattr(challenge, key, value)
                        changed = True
                active_flags = await session.scalars(select(ChallengeFlag).where(ChallengeFlag.challenge_id == challenge.id, ChallengeFlag.is_active.is_(True)))
                if not list(active_flags) and item.get("flag_values"):
                    for order, flag_value in enumerate(item["flag_values"], start=1):
                        session.add(ChallengeFlag(challenge_id=challenge.id, label=f"Flag {order}", flag_hash=hash_password(flag_value), flag_order=order, is_active=True))
                    changed = True
                if changed:
                    session.add(challenge)
        await session.commit()


async def ranking_rows(session_factory) -> list[dict]:
    async with session_factory() as session:
        statement = (
            select(
                User.username,
                func.coalesce(func.sum(ChallengeCompletion.awarded_points), 0).label("total_points"),
                func.count(ChallengeCompletion.id).label("challenges_completed"),
            )
            .outerjoin(ChallengeCompletion, ChallengeCompletion.user_id == User.id)
            .where(User.role == "player", User.is_active.is_(True))
            .group_by(User.id, User.username)
            .order_by(func.coalesce(func.sum(ChallengeCompletion.awarded_points), 0).desc(), func.min(ChallengeCompletion.completed_at).asc().nullslast(), User.username.asc())
        )
        data = (await session.execute(statement)).all()
        return [
            {"position": index, "username": row.username, "total_points": int(row.total_points), "challenges_completed": int(row.challenges_completed)}
            for index, row in enumerate(data, start=1)
        ]


async def check_rate_limit(redis_client, key: str, maximum: int = 8, window_seconds: int = 60) -> None:
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count > maximum:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados intentos. Espera un minuto antes de continuar.")
    except HTTPException:
        raise
    except Exception:
        # Redis mejora la defensa, pero una indisponibilidad no debe convertir la plataforma en una denegación de servicio.
        return


def challenge_view(challenge: Challenge, completed: bool = False, include_flags: bool = False) -> ChallengeView:
    flags = None
    if include_flags:
        flags = [{"id": item.id, "label": item.label, "flag_order": item.flag_order, "is_active": item.is_active, "mode": item.mode, "template": item.template} for item in challenge.flags]
    return ChallengeView(
        id=challenge.id,
        code=challenge.code,
        name=challenge.name,
        description=challenge.description,
        instructions=challenge.instructions,
        difficulty=challenge.difficulty,
        category=challenge.category,
        scenario=challenge.scenario,
        mitre_technique=challenge.mitre_technique,
        asset_references=challenge.asset_references,
        points=challenge.points,
        is_published=challenge.is_published,
        flag_count=len(challenge.flags),
        completed=completed,
        flags=flags,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.session_factory = make_session_factory()
    await create_schema(app.state.session_factory)
    await seed_data(app.state.session_factory)
    app.state.redis = redis.from_url(get_settings().redis_url, decode_responses=True)
    app.state.guacamole = make_guacamole_adapter()
    app.state.guacamole_admin = make_guacamole_admin()
    app.state.sockets = ConnectionManager()
    yield
    await app.state.redis.aclose()




# ============================================================
# CONFIGURACIÓN Y CICLO DE VIDA DE LA API
# Responsabilidad: inicializar recursos compartidos, CORS y servicios.
# ============================================================

app = FastAPI(title="Plataforma CTF del laboratorio", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().public_origin, "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================
# AUTENTICACIÓN Y SESIÓN
# ============================================================

@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "service": "ctf-api"}


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request):
    await check_rate_limit(request.app.state.redis, f"rate:login:{payload.username}", maximum=10)
    async with request.app.state.session_factory() as session:
        user = await session.scalar(select(User).where(User.username == payload.username))
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
        await write_audit(session, user.id, "auth.login", "user", str(user.id))
        await session.commit()
    token = create_token(str(user.id), "access", timedelta(minutes=get_settings().access_token_minutes))
    return TokenResponse(access_token=token, user=UserView.model_validate(user))


@app.get("/api/v1/auth/me", response_model=UserView)
async def me(user=Depends(get_current_user)):
    return UserView.model_validate(user)

@app.patch("/api/v1/auth/profile", response_model=UserView)
async def update_profile(payload: ProfileUpdate, request: Request, actor=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, actor.id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        username = payload.username.strip()
        existing = await session.scalar(select(User).where(User.username == username, User.id != actor.id))
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre")
        if payload.email:
            existing_email = await session.scalar(select(User).where(User.email == payload.email, User.id != actor.id))
            if existing_email:
                raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
        target.username = username
        target.email = payload.email
        await write_audit(session, actor.id, "profile.update", "user", str(actor.id), {"fields": ["username", "email"]})
        await session.commit()
        await session.refresh(target)
        return UserView.model_validate(target)

@app.post("/api/v1/auth/password")
async def change_password(payload: PasswordChange, request: Request, actor=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, actor.id)
        if target is None or not verify_password(payload.current_password, target.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
        target.password_hash = hash_password(payload.new_password)
        await write_audit(session, actor.id, "profile.password_change", "user", str(actor.id))
        await session.commit()
    return {"ok": True}


# ============================================================
# RETOS, FLAGS Y PROGRESO
# Responsabilidad: catálogo, configuración de flags y ejecución del CTF.
# ============================================================

@app.get("/api/v1/challenges", response_model=list[ChallengeView])
async def list_challenges(request: Request, difficulty: str | None = None, category: str | None = None, mitre: str | None = None, user=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        statement = select(Challenge).options(selectinload(Challenge.flags))
        if user.role not in ("admin", "instructor"):
            statement = statement.where(Challenge.is_published.is_(True))
            # Un reto para jugadores solo es visible si está asignado a uno de sus grupos.
            # Si no tiene asignaciones, se considera no publicado para estudiantes.
            assigned_exists = select(ChallengeGroupAssignment.id).join(
                GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id
            ).join(
                StudentGroup, StudentGroup.id == GroupMembership.group_id
            ).where(
                ChallengeGroupAssignment.challenge_id == Challenge.id,
                GroupMembership.user_id == user.id,
                StudentGroup.is_active.is_(True),
            ).exists()
            statement = statement.where(assigned_exists)
        if difficulty:
            statement = statement.where(Challenge.difficulty == difficulty)
        if category:
            statement = statement.where(Challenge.category.ilike(category))
        if mitre:
            statement = statement.where(Challenge.mitre_technique.ilike(f"%{mitre}%"))
        statement = statement.order_by(Challenge.difficulty, Challenge.code)
        challenges = (await session.scalars(statement)).unique().all()
        completed_ids = set((await session.scalars(select(ChallengeCompletion.challenge_id).where(ChallengeCompletion.user_id == user.id))).all())
        include_flags = user.role in ("admin", "instructor")
        result = [challenge_view(item, item.id in completed_ids, include_flags) for item in challenges]
        if user.role == "guest":
            # El invitado conoce el catálogo, pero no obtiene instrucciones ni referencias de acceso.
            for item in result:
                item.instructions = "Acceso disponible únicamente para jugadores autorizados."
                item.asset_references = ["Información de acceso restringida"]
        return result


@app.get("/api/v1/categories")
async def list_categories(request: Request, user=Depends(get_current_user)):
    async with request.app.state.session_factory() as session:
        statement = select(Challenge.category, func.count(Challenge.id)).where(Challenge.is_published.is_(True)).group_by(Challenge.category).order_by(Challenge.category)
        rows = (await session.execute(statement)).all()
        return [{"name": name, "challenge_count": int(count)} for name, count in rows]


# ============================================================
# USUARIOS Y ROLES
# Responsabilidad: aplicar autorización y mantener cuentas CTF.
# ============================================================

@app.get("/api/v1/users", response_model=list[UserView])
async def list_users(request: Request, _=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        users = (await session.scalars(select(User).order_by(User.username))).all()
        return [UserView.model_validate(item) for item in users]


@app.get("/api/v1/users/visible", response_model=list[UserView])
async def list_visible_users(request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        statement = select(User).order_by(User.username)
        if actor.role == "instructor":
            statement = statement.where(User.role != "admin")
        users = (await session.scalars(statement)).all()
        return [UserView.model_validate(item) for item in users]


@app.post("/api/v1/users", response_model=UserView, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        if await session.scalar(select(User).where(User.username == payload.username)):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre")
        if payload.email and await session.scalar(select(User).where(User.email == payload.email)):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

        created_in_guac = False
        if payload.sync_guacamole:
            try:
                existing = {item.username for item in await request.app.state.guacamole_admin.list_users()}
                if payload.username in existing:
                    raise HTTPException(status_code=409, detail="El usuario ya existe en Guacamole")
                await request.app.state.guacamole_admin.create_user(
                    payload.username,
                    payload.password,
                    email=payload.email,
                    full_name=payload.full_name,
                )
                created_in_guac = True
            except HTTPException:
                raise
            except GuacamoleApiError as exc:
                raise HTTPException(status_code=502, detail=f"No se pudo crear la cuenta en Guacamole: {exc}") from exc

        target = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            full_name=payload.full_name,
            organization=payload.organization,
            user_function=payload.user_function,
            is_active=True,
        )
        session.add(target)
        try:
            await session.flush()
            await write_audit(session, actor.id, "user.create", "user", str(target.id), {"role": payload.role, "guacamole": payload.sync_guacamole})
            await session.commit()
        except Exception:
            await session.rollback()
            if created_in_guac:
                try:
                    await request.app.state.guacamole_admin.delete_user(payload.username)
                except Exception:
                    pass
            raise
        await session.refresh(target)
        return UserView.model_validate(target)


@app.get("/api/v1/admin/guacamole/status", response_model=GuacamoleStatus)
async def guacamole_status(request: Request, _=Depends(require_roles("admin"))):
    try:
        return await request.app.state.guacamole_admin.status()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/admin/guacamole/users", response_model=list[GuacamoleUserView])
async def guacamole_users(request: Request, _=Depends(require_roles("admin"))):
    try:
        users = await request.app.state.guacamole_admin.list_users()
        return [GuacamoleUserView(username=item.username, attributes=item.attributes, last_active=item.last_active) for item in users]
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/admin/guacamole/users", response_model=GuacamoleUserView, status_code=status.HTTP_201_CREATED)
async def guacamole_create_user(payload: GuacamoleUserCreate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        created = await request.app.state.guacamole_admin.create_user(
            payload.username, payload.password, email=payload.email, full_name=payload.full_name
        )
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.create", "guacamole_user", payload.username)
            await session.commit()
        return GuacamoleUserView(username=created.username, attributes=created.attributes, last_active=created.last_active)
    except GuacamoleApiError as exc:
        code = 409 if exc.status_code in (400, 409) else 502
        raise HTTPException(status_code=code, detail=exc.detail or str(exc)) from exc


@app.patch("/api/v1/admin/guacamole/users/{username}", response_model=GuacamoleUserView)
async def guacamole_update_user(username: str, payload: GuacamoleUserUpdate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        updated = await request.app.state.guacamole_admin.update_user(
            username, password=payload.password, email=payload.email, full_name=payload.full_name, disabled=payload.disabled
        )
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.update", "guacamole_user", username, payload.model_dump(exclude_none=True))
            await session.commit()
        return GuacamoleUserView(username=updated.username, attributes=updated.attributes, last_active=updated.last_active)
    except GuacamoleApiError as exc:
        code = 404 if exc.status_code == 404 else 502
        raise HTTPException(status_code=code, detail=exc.detail or str(exc)) from exc


@app.delete("/api/v1/admin/guacamole/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def guacamole_delete_user(username: str, request: Request, actor=Depends(require_roles("admin"))):
    if username == get_settings().guacamole_service_account:
        raise HTTPException(status_code=409, detail="No puedes eliminar la cuenta de servicio de Guacamole")
    try:
        await request.app.state.guacamole_admin.delete_user(username)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.delete", "guacamole_user", username)
            await session.commit()
    except GuacamoleApiError as exc:
        code = 404 if exc.status_code == 404 else 502
        raise HTTPException(status_code=code, detail=exc.detail or str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/v1/admin/guacamole/connections", response_model=list[GuacamoleConnectionView])
async def guacamole_connections(request: Request, _=Depends(require_roles("admin"))):
    try:
        rows = await request.app.state.guacamole_admin.list_connections()
        return [GuacamoleConnectionView(identifier=x.identifier, name=x.name, protocol=x.protocol, parent_identifier=x.parent_identifier, hostname=x.hostname, port=x.port, parameters=x.parameters or {}, attributes=x.attributes or {}, active_connections=x.active_connections) for x in rows]
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=exc.detail or str(exc)) from exc


@app.post("/api/v1/admin/guacamole/connections", response_model=GuacamoleConnectionView, status_code=status.HTTP_201_CREATED)
async def guacamole_create_connection(payload: GuacamoleConnectionCreate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        c = await request.app.state.guacamole_admin.create_connection(name=payload.name, protocol=payload.protocol, hostname=payload.hostname, port=payload.port, username=payload.username, password=payload.password, domain=payload.domain, parent_identifier=payload.parent_identifier)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.create", "guacamole_connection", c.identifier, {"name": c.name, "protocol": c.protocol, "hostname": c.hostname, "port": c.port}); await session.commit()
        return GuacamoleConnectionView(identifier=c.identifier, name=c.name, protocol=c.protocol, parent_identifier=c.parent_identifier, hostname=c.hostname, port=c.port, parameters=c.parameters or {}, attributes=c.attributes or {}, active_connections=c.active_connections)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=409 if exc.status_code in (400,409) else 502, detail=exc.detail or str(exc)) from exc


@app.put("/api/v1/admin/guacamole/connections/{identifier}", response_model=GuacamoleConnectionView)
async def guacamole_update_connection(identifier: str, payload: GuacamoleConnectionUpdate, request: Request, actor=Depends(require_roles("admin"))):
    try:
        c = await request.app.state.guacamole_admin.update_connection(identifier, name=payload.name, protocol=payload.protocol, hostname=payload.hostname, port=payload.port, username=payload.username, password=payload.password, domain=payload.domain, parent_identifier=payload.parent_identifier)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.update", "guacamole_connection", identifier, {"name": c.name, "protocol": c.protocol, "hostname": c.hostname, "port": c.port}); await session.commit()
        return GuacamoleConnectionView(identifier=c.identifier, name=c.name, protocol=c.protocol, parent_identifier=c.parent_identifier, hostname=c.hostname, port=c.port, parameters=c.parameters or {}, attributes=c.attributes or {}, active_connections=c.active_connections)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc


@app.delete("/api/v1/admin/guacamole/connections/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def guacamole_delete_connection(identifier: str, request: Request, actor=Depends(require_roles("admin"))):
    try:
        await request.app.state.guacamole_admin.delete_connection(identifier)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.connection.delete", "guacamole_connection", identifier); await session.commit()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/v1/admin/guacamole/users/{username}/permissions", response_model=GuacamolePermissionSet)
async def guacamole_get_permissions(username: str, request: Request, _=Depends(require_roles("admin"))):
    if username == get_settings().guacamole_service_account:
        data = {"systemPermissions": ["ADMINISTER"], "connectionPermissions": {}}
    else:
        try: data = await request.app.state.guacamole_admin.get_user_permissions(username)
        except GuacamoleApiError as exc: raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc
    return GuacamolePermissionSet(system_permissions=list(data.get("systemPermissions") or []), connection_permissions={str(k): list(v or []) for k,v in (data.get("connectionPermissions") or {}).items()})


@app.patch("/api/v1/admin/guacamole/users/{username}/permissions", response_model=GuacamolePermissionSet)
async def guacamole_patch_permissions(username: str, payload: GuacamolePermissionPatch, request: Request, actor=Depends(require_roles("admin"))):
    if username == get_settings().guacamole_service_account:
        raise HTTPException(status_code=409, detail="La cuenta de servicio no puede ser administrada desde el panel")
    allowed_system = {"ADMINISTER", "CREATE_CONNECTION", "CREATE_CONNECTION_GROUP", "CREATE_SHARING_PROFILE", "CREATE_USER", "CREATE_USER_GROUP"}
    allowed_object = {"READ", "UPDATE", "DELETE", "ADMINISTER"}
    if any(x not in allowed_system for x in payload.system_permissions) or any(x not in allowed_object for values in payload.connection_permissions.values() for x in values):
        raise HTTPException(status_code=422, detail="Permiso de Guacamole no válido")
    try:
        data = await request.app.state.guacamole_admin.patch_user_permissions(username, system_permissions=payload.system_permissions, connection_permissions=payload.connection_permissions)
        async with request.app.state.session_factory() as session:
            await write_audit(session, actor.id, "guacamole.user.permissions", "guacamole_user", username, {"system_permissions": payload.system_permissions, "connection_permissions": payload.connection_permissions}); await session.commit()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=404 if exc.status_code == 404 else 502, detail=exc.detail or str(exc)) from exc
    return GuacamolePermissionSet(system_permissions=list(data.get("systemPermissions") or []), connection_permissions={str(k): list(v or []) for k,v in (data.get("connectionPermissions") or {}).items()})


@app.patch("/api/v1/users/{user_id}", response_model=UserView)
async def update_user(user_id: int, payload: UserUpdate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if target.id == actor.id and payload.is_active is False:
            raise HTTPException(status_code=409, detail="No puedes deshabilitar tu propia cuenta")
        values = payload.model_dump(exclude_none=True)
        if target.role in {"admin", "instructor"} and "role" in values and values["role"] != target.role:
            raise HTTPException(status_code=403, detail="Las cuentas de administrador e instructor están protegidas contra cambio de rol")
        if target.id == actor.id and "role" in values and values["role"] != target.role:
            raise HTTPException(status_code=403, detail="No puedes cambiar tu propio rol desde este panel")
        for field, value in values.items():
            setattr(target, field, value)
        if {"is_active", "full_name", "organization"}.intersection(values):
            try:
                await request.app.state.guacamole_admin.update_user(target.username, full_name=target.full_name, disabled=not target.is_active)
            except GuacamoleApiError as exc:
                if exc.status_code != 404:
                    raise HTTPException(status_code=502, detail=f"No se pudo sincronizar el acceso de Guacamole: {exc.detail or exc}") from exc
        await write_audit(session, actor.id, "user.update", "user", str(target.id), values)
        await session.commit()
        await session.refresh(target)
        return UserView.model_validate(target)


@app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if target.id == actor.id:
            raise HTTPException(status_code=403, detail="No puedes eliminar tu propia cuenta")
        if target.role == "admin":
            admin_count = await session.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True)))
            if int(admin_count or 0) <= 1:
                raise HTTPException(status_code=409, detail="Debe existir al menos un administrador activo")
        try:
            remotes = await request.app.state.guacamole_admin.list_users()
            if any(item.username == target.username for item in remotes):
                await request.app.state.guacamole_admin.delete_user(target.username)
        except GuacamoleApiError as exc:
            if exc.status_code != 404:
                raise HTTPException(status_code=502, detail=f"No se pudo eliminar la cuenta de Guacamole: {exc.detail or exc}") from exc
        await write_audit(session, actor.id, "user.delete", "user", str(target.id), {"username": target.username, "role": target.role, "guacamole": True})
        await session.delete(target)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ============================================================
# LABORATORIOS Y MÁQUINAS VIRTUALES
# Responsabilidad: persistir inventario, redes e IPs disponibles.
# ============================================================

async def _group_view(request: Request, group_id: int) -> GroupView:
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id, options=[selectinload(StudentGroup.members).selectinload(GroupMembership.user), selectinload(StudentGroup.challenge_assignments).selectinload(ChallengeGroupAssignment.challenge)])
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        return GroupView.from_model(group)


@app.get("/api/v1/groups", response_model=list[GroupView])
async def list_groups(request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        groups = (await session.scalars(
            select(StudentGroup)
            .options(
                selectinload(StudentGroup.members).selectinload(GroupMembership.user),
                selectinload(StudentGroup.challenge_assignments).selectinload(ChallengeGroupAssignment.challenge),
            )
            .order_by(StudentGroup.name)
        )).unique().all()
        return [GroupView.from_model(group) for group in groups]


async def _group_view(request: Request, group_id: int) -> GroupView:
    async with request.app.state.session_factory() as session:
        group = await session.get(
            StudentGroup,
            group_id,
            options=[
                selectinload(StudentGroup.members).selectinload(GroupMembership.user),
                selectinload(StudentGroup.challenge_assignments).selectinload(ChallengeGroupAssignment.challenge),
            ],
        )
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        return GroupView.from_model(group)


@app.post("/api/v1/groups", response_model=GroupView, status_code=status.HTTP_201_CREATED)
async def create_group(payload: GroupCreate, request: Request, actor=Depends(require_roles("admin"))):
    guac_identifier = payload.code.strip().upper()
    created_in_guac = False
    try:
        await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=not payload.is_active)
        created_in_guac = True
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502 if exc.status_code not in (400,409) else 409, detail=f"No se pudo crear el grupo en Guacamole: {exc.detail or exc}") from exc

    async with request.app.state.session_factory() as session:
        if await session.scalar(select(StudentGroup).where(StudentGroup.code == payload.code)):
            if created_in_guac:
                try: await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
                except Exception: pass
            raise HTTPException(status_code=409, detail="Ya existe un grupo con ese código")
        if await session.scalar(select(StudentGroup).where(StudentGroup.name == payload.name)):
            if created_in_guac:
                try: await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
                except Exception: pass
            raise HTTPException(status_code=409, detail="Ya existe un grupo con ese nombre")
        group = StudentGroup(name=payload.name, code=payload.code, description=payload.description, is_active=payload.is_active, guacamole_group_identifier=guac_identifier, created_by=actor.id)
        session.add(group)
        try:
            await session.flush()
            await write_audit(session, actor.id, "group.create", "group", str(group.id), {**payload.model_dump(), "guacamole_group": guac_identifier})
            await session.commit()
        except Exception:
            await session.rollback()
            if created_in_guac:
                try: await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
                except Exception: pass
            raise
    return await _group_view(request, group.id)


@app.patch("/api/v1/groups/{group_id}", response_model=GroupView)
async def update_group(group_id: int, payload: GroupCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        duplicate_code = await session.scalar(select(StudentGroup).where(StudentGroup.code == payload.code, StudentGroup.id != group_id))
        duplicate_name = await session.scalar(select(StudentGroup).where(StudentGroup.name == payload.name, StudentGroup.id != group_id))
        if duplicate_code or duplicate_name:
            raise HTTPException(status_code=409, detail="Ya existe otro grupo con ese código o nombre")
        group.name = payload.name
        group.code = payload.code
        group.description = payload.description
        group.is_active = payload.is_active
        guac_identifier = group.guacamole_group_identifier or payload.code
        group.guacamole_group_identifier = guac_identifier
        await write_audit(session, actor.id, "group.update", "group", str(group.id), {**payload.model_dump(), "guacamole_group": guac_identifier})
        await session.commit()
    try:
        if guac_identifier:
            try:
                await request.app.state.guacamole_admin.update_user_group(guac_identifier, disabled=not payload.is_active)
            except GuacamoleApiError as exc:
                if exc.status_code == 404:
                    await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=not payload.is_active)
                else:
                    raise
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo sincronizar el grupo con Guacamole: {exc.detail or exc}") from exc
    return await _group_view(request, group_id)


@app.delete("/api/v1/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id, options=[selectinload(StudentGroup.members)])
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        member_ids = [member.user_id for member in group.members]
        guac_identifier = group.guacamole_group_identifier or group.code
        await write_audit(session, actor.id, "group.delete", "group", str(group.id), {"name": group.name, "code": group.code, "member_count": len(member_ids), "guacamole_group": guac_identifier})
        await session.delete(group)
        await session.commit()
    if guac_identifier:
        try:
            await request.app.state.guacamole_admin.delete_user_group(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code != 404:
                raise HTTPException(status_code=502, detail=f"No se pudo eliminar el grupo de Guacamole: {exc.detail or exc}") from exc
    for user_id in member_ids:
        await _sync_player_guacamole_permissions(request, int(user_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/v1/groups/{group_id}/members", response_model=GroupView)
async def add_group_member(group_id: int, payload: GroupMemberAdd, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        target = await session.get(User, payload.user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        if target is None or target.role != "player" or not target.is_active:
            raise HTTPException(status_code=422, detail="Solo se pueden agregar estudiantes activos")
        exists = await session.scalar(select(GroupMembership).where(GroupMembership.group_id == group_id, GroupMembership.user_id == payload.user_id))
        if not exists:
            session.add(GroupMembership(group_id=group_id, user_id=payload.user_id))
            await write_audit(session, actor.id, "group.member.add", "group", str(group_id), {"user_id": payload.user_id})
            await session.commit()
    async with request.app.state.session_factory() as session:
        row = await session.get(StudentGroup, group_id)
        target = await session.get(User, payload.user_id)
        guac_identifier = row.guacamole_group_identifier if row else None
        username = target.username if target else None
        if row is not None and not guac_identifier:
            guac_identifier = row.code
            row.guacamole_group_identifier = guac_identifier
            await session.commit()
    if guac_identifier and username:
        try:
            await request.app.state.guacamole_admin.get_user_group_permissions(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code == 404:
                try: await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=False)
                except GuacamoleApiError as create_exc:
                    raise HTTPException(status_code=502, detail=f"No se pudo crear el grupo en Guacamole: {create_exc.detail or create_exc}") from create_exc
            else:
                raise HTTPException(status_code=502, detail=f"No se pudo verificar el grupo en Guacamole: {exc.detail or exc}") from exc
        try: await request.app.state.guacamole_admin.add_user_group_member(guac_identifier, username)
        except GuacamoleApiError as exc:
            raise HTTPException(status_code=502, detail=f"No se pudo añadir el estudiante al grupo de Guacamole: {exc.detail or exc}") from exc
    await _sync_player_guacamole_permissions(request, payload.user_id)
    return await _group_view(request, group_id)


@app.delete("/api/v1/groups/{group_id}/members/{user_id}", response_model=GroupView)
async def remove_group_member(group_id: int, user_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        membership = await session.scalar(select(GroupMembership).where(GroupMembership.group_id == group_id, GroupMembership.user_id == user_id))
        if membership:
            await session.delete(membership)
            await write_audit(session, actor.id, "group.member.remove", "group", str(group_id), {"user_id": user_id})
            await session.commit()
    async with request.app.state.session_factory() as session:
        row = await session.get(StudentGroup, group_id)
        target = await session.get(User, user_id)
        guac_identifier = row.guacamole_group_identifier if row else None
        username = target.username if target else None
    if guac_identifier and username:
        try: await request.app.state.guacamole_admin.remove_user_group_member(guac_identifier, username)
        except GuacamoleApiError as exc:
            if exc.status_code != 404:
                raise HTTPException(status_code=502, detail=f"No se pudo retirar el estudiante del grupo de Guacamole: {exc.detail or exc}") from exc
    await _sync_player_guacamole_permissions(request, user_id)
    return await _group_view(request, group_id)


@app.put("/api/v1/challenges/{code}/groups/{group_id}", response_model=GroupView)
async def assign_challenge_group(code: str, group_id: int, request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
        group = await session.get(StudentGroup, group_id)
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        if group is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        exists = await session.scalar(select(ChallengeGroupAssignment).where(ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group_id))
        if not exists:
            session.add(ChallengeGroupAssignment(challenge_id=challenge.id, group_id=group_id, created_by=actor.id))
            await write_audit(session, actor.id, "challenge.group.assign", "challenge", str(challenge.id), {"group_id": group_id, "code": code})
            await session.commit()
    await _sync_guacamole_group_permissions(request, group_id)
    return await _group_view(request, group_id)


@app.delete("/api/v1/challenges/{code}/groups/{group_id}", response_model=GroupView)
async def unassign_challenge_group(code: str, group_id: int, request: Request, actor=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        assignment = await session.scalar(select(ChallengeGroupAssignment).where(ChallengeGroupAssignment.challenge_id == challenge.id, ChallengeGroupAssignment.group_id == group_id))
        if assignment:
            await session.delete(assignment)
            await write_audit(session, actor.id, "challenge.group.unassign", "challenge", str(challenge.id), {"group_id": group_id, "code": code})
            await session.commit()
    await _sync_guacamole_group_permissions(request, group_id)
    return await _group_view(request, group_id)


@app.get("/api/v1/laboratories", response_model=list[LaboratoryView])
async def list_laboratories(request: Request, _=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        labs = (await session.scalars(select(Laboratory).options(selectinload(Laboratory.vms)).order_by(Laboratory.id))).unique().all()
        return [laboratory_view(item) for item in labs]

@app.get("/api/v1/player/laboratories", response_model=list[LaboratoryView])
async def list_player_laboratories(request: Request, user=Depends(require_roles("player"))):
    async with request.app.state.session_factory() as session:
        assigned_challenge_ids = select(ChallengeGroupAssignment.challenge_id).join(
            GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id
        ).join(
            StudentGroup, StudentGroup.id == GroupMembership.group_id
        ).where(
            GroupMembership.user_id == user.id,
            StudentGroup.is_active.is_(True),
        )
        challenges = (await session.scalars(
            select(Challenge).where(Challenge.is_published.is_(True), Challenge.id.in_(assigned_challenge_ids))
        )).all()
        refs = {ref for challenge in challenges for ref in (challenge.asset_references or [])}
        if not refs:
            return []
        labs = (await session.scalars(
            select(Laboratory).options(selectinload(Laboratory.vms)).where(
                Laboratory.status.in_(("ready", "planned")),
            ).order_by(Laboratory.id)
        )).unique().all()
        response: list[LaboratoryView] = []
        normalized_refs = {_asset_ref_key(ref) for ref in refs}
        for lab in labs:
            lab_keys = {_asset_ref_key(lab.name), _asset_ref_key(lab.code or "")}
            matching_lab = bool(normalized_refs.intersection(lab_keys))
            vm_views: list[VMView] = []
            for vm in lab.vms:
                if not matching_lab and _asset_ref_key(vm.name) not in normalized_refs:
                    continue
                guac_url = None
                guac_protocol = None
                if vm.guacamole_connection_id:
                    try:
                        connections = await request.app.state.guacamole_admin.list_connections()
                        conn = next((item for item in connections if item.identifier == vm.guacamole_connection_id), None)
                        if conn:
                            guac_protocol = conn.protocol
                            guac_url = await request.app.state.guacamole.direct_connection_url(conn.identifier)
                    except Exception:
                        guac_url = None
                vm_views.append(vm_view(vm, guacamole_url=guac_url, guacamole_protocol=guac_protocol))
            if vm_views:
                response.append(LaboratoryView(id=lab.id, code=lab.code, name=lab.name, description=lab.description, segment=lab.segment, status=lab.status, vms=vm_views))
        return response

@app.post("/api/v1/laboratories", response_model=LaboratoryView, status_code=status.HTTP_201_CREATED)
async def create_laboratory(payload: LaboratoryCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        if await session.scalar(select(Laboratory).where(Laboratory.name == payload.name)):
            raise HTTPException(status_code=409, detail="Ya existe un laboratorio con ese nombre")
        if payload.code and await session.scalar(select(Laboratory).where(Laboratory.code == payload.code)):
            raise HTTPException(status_code=409, detail="Ya existe un laboratorio con ese código")
        item = Laboratory(**payload.model_dump())
        session.add(item)
        await session.flush()
        await write_audit(session, actor.id, "laboratory.create", "laboratory", str(item.id), payload.model_dump())
        await session.commit()
        await session.refresh(item, attribute_names=["vms"])
        return laboratory_view(item)

@app.patch("/api/v1/laboratories/{laboratory_id}", response_model=LaboratoryView)
async def update_laboratory(laboratory_id: int, payload: LaboratoryCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(Laboratory, laboratory_id, options=[selectinload(Laboratory.vms)])
        if item is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        item.code = payload.code
        item.name = payload.name
        item.description = payload.description
        item.segment = payload.segment
        item.status = payload.status
        await write_audit(session, actor.id, "laboratory.update", "laboratory", str(item.id), payload.model_dump())
        await session.commit()
        await session.refresh(item, attribute_names=["vms"])
        return laboratory_view(item)

@app.delete("/api/v1/laboratories/{laboratory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_laboratory(laboratory_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(Laboratory, laboratory_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        await write_audit(session, actor.id, "laboratory.delete", "laboratory", str(item.id), {"name": item.name})
        await session.delete(item)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/api/v1/vms", response_model=VMView, status_code=status.HTTP_201_CREATED)
async def create_vm(payload: VMCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        lab = await session.get(Laboratory, payload.laboratory_id)
        if lab is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        if payload.ip_address:
            allowed = DEMO_VM_IPS.get(payload.network_role, set())
            if payload.ip_address not in allowed:
                raise HTTPException(status_code=422, detail="La IP seleccionada no pertenece al catálogo actual del laboratorio")
            used = await session.scalar(select(VMAsset).where(VMAsset.ip_address == payload.ip_address))
            if used:
                raise HTTPException(status_code=409, detail="La dirección IP ya está asignada")
        item = VMAsset(**payload.model_dump())
        session.add(item)
        await session.flush()
        await write_audit(session, actor.id, "vm.create", "vm", str(item.id), payload.model_dump())
        await session.commit()
        return vm_view(item)

@app.patch("/api/v1/vms/{vm_id}", response_model=VMView)
async def update_vm(vm_id: int, payload: VMCreate, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(VMAsset, vm_id)
        if item is None:
            raise HTTPException(status_code=404, detail="VM no encontrada")
        lab = await session.get(Laboratory, payload.laboratory_id)
        if lab is None:
            raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
        if payload.ip_address:
            allowed = DEMO_VM_IPS.get(payload.network_role, set())
            if payload.ip_address not in allowed:
                raise HTTPException(status_code=422, detail="La IP seleccionada no pertenece al catálogo actual del laboratorio")
            used = await session.scalar(select(VMAsset).where(VMAsset.ip_address == payload.ip_address, VMAsset.id != vm_id))
            if used:
                raise HTTPException(status_code=409, detail="La dirección IP ya está asignada")
        for field, value in payload.model_dump().items():
            if field != "laboratory_id":
                setattr(item, field, value)
        item.laboratory_id = payload.laboratory_id
        await write_audit(session, actor.id, "vm.update", "vm", str(item.id), payload.model_dump())
        await session.commit()
        await session.refresh(item)
        return vm_view(item)

@app.delete("/api/v1/vms/{vm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vm(vm_id: int, request: Request, actor=Depends(require_roles("admin"))):
    async with request.app.state.session_factory() as session:
        item = await session.get(VMAsset, vm_id)
        if item is None:
            raise HTTPException(status_code=404, detail="VM no encontrada")
        await write_audit(session, actor.id, "vm.delete", "vm", str(item.id), {"name": item.name})
        await session.delete(item)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/v1/admin/lab-ssh/prepare")
async def prepare_ssh_demo_lab(request: Request, actor=Depends(require_roles("admin"))):
    """Prepara el laboratorio real SSH de demostración usando la VM/IP actuales y una conexión SSH existente en Guacamole."""
    target_ip = "192.168.164.137"
    attacker_ip = "192.168.146.134"
    lab_code = "LAB-SSH-01"
    vm_name = "LAB-LNXVICT"
    challenge_code = "LAB-01"
    static_flag = "FLAG{ssh_lab_demo}"

    try:
        connections = await request.app.state.guacamole_admin.list_connections()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar Guacamole: {exc.detail or exc}") from exc

    connection = next((c for c in connections if c.protocol == "ssh" and (c.hostname or "").strip() == target_ip), None)
    if connection is None:
        raise HTTPException(status_code=409, detail=f"No existe una conexión SSH de Guacamole asociada a {target_ip}. Créala primero en Administración > Guacamole.")

    async with request.app.state.session_factory() as session:
        lab = await session.scalar(select(Laboratory).options(selectinload(Laboratory.vms)).where(Laboratory.code == lab_code))
        if lab is None:
            lab = Laboratory(code=lab_code, name="Laboratorio SSH · Demostración", description="Laboratorio real de reconocimiento controlado sobre la VM LAB-LNXVICT.", segment="Red actual · Víctima 192.168.164.137", status="ready")
            session.add(lab)
            await session.flush()
        else:
            lab.status = "ready"

        vm = await session.scalar(select(VMAsset).where(VMAsset.name == vm_name))
        if vm is None:
            vm = VMAsset(laboratory_id=lab.id, name=vm_name, os="Linux / VM de laboratorio", ip_address=target_ip, vlan="RED ACTUAL", role="Víctima", network_role="Víctimas", subnet="192.168.164.0/24", profile="vulnerable", status="ready", guacamole_connection_id=connection.identifier)
            session.add(vm)
        else:
            vm.laboratory_id = lab.id
            vm.ip_address = target_ip
            vm.network_role = "Víctimas"
            vm.role = "Víctima"
            vm.guacamole_connection_id = connection.identifier
            vm.status = "ready"

        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == challenge_code))
        challenge_payload = {
            "name": "Reconocimiento SSH controlado",
            "description": "Identifica el servicio SSH de la máquina víctima del laboratorio y localiza la evidencia del ejercicio.",
            "instructions": "Trabaja únicamente dentro del laboratorio autorizado. Desde la Kali atacante identifica el servicio SSH en 192.168.164.137, conéctate con las credenciales proporcionadas por el instructor y localiza /opt/ctf/flag.txt. No realices acciones fuera del entorno.",
            "difficulty": "Básico",
            "category": "MISC",
            "scenario": "LAB-SSH-REAL",
            "mitre_technique": "T1046 — Network Service Scanning",
            "asset_references": [vm_name, lab_code, target_ip],
            "points": 100,
            "is_published": True,
        }
        if challenge is None:
            challenge = Challenge(**challenge_payload, created_by=actor.id)
            session.add(challenge)
            await session.flush()
        else:
            for key, value in challenge_payload.items():
                setattr(challenge, key, value)

        active_static = next((f for f in challenge.flags if f.is_active and f.mode == "static"), None)
        if active_static is None:
            session.add(ChallengeFlag(challenge_id=challenge.id, label="Flag SSH", flag_hash=hash_password(static_flag), flag_order=1, is_active=True, mode="static"))
        else:
            active_static.flag_hash = hash_password(static_flag)
            active_static.mode = "static"
            active_static.template = None
            active_static.label = "Flag SSH"
            active_static.flag_order = 1
        await write_audit(session, actor.id, "lab.demo.prepare", "laboratory", str(lab.id), {"lab_code": lab_code, "vm": vm_name, "ip": target_ip, "attacker_ip": attacker_ip, "guacamole_connection": connection.identifier, "challenge": challenge_code})
        await session.commit()

    return {
        "laboratory": {"id": lab.id, "code": lab.code, "name": lab.name},
        "vm": {"id": vm.id, "name": vm.name, "ip": vm.ip_address, "protocol": connection.protocol, "guacamole_connection_id": connection.identifier, "guacamole_connection_name": connection.name},
        "challenge": {"code": challenge.code, "name": challenge.name, "points": challenge.points, "flag_mode": "static"},
        "attacker_ip": attacker_ip,
        "victim_ip": target_ip,
        "flag": "FLAG{ssh_lab_demo}",
        "note": "La flag estática se valida por hash. La VM ya debe contener /opt/ctf/flag.txt con el mismo valor.",
    }

@app.post("/api/v1/challenges", response_model=ChallengeView, status_code=status.HTTP_201_CREATED)
async def create_challenge(payload: ChallengeCreate, request: Request, user=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        if await session.scalar(select(Challenge).where(Challenge.code == payload.code)):
            raise HTTPException(status_code=409, detail="Ya existe un reto con ese código")
        challenge = Challenge(**payload.model_dump(), created_by=user.id)
        session.add(challenge)
        await session.flush()
        await write_audit(session, user.id, "challenge.create", "challenge", str(challenge.id), {"code": challenge.code})
        await session.commit()
        await session.refresh(challenge, attribute_names=["flags"])
        return challenge_view(challenge, include_flags=True)


@app.put("/api/v1/challenges/{code}", response_model=ChallengeView)
async def update_challenge(code: str, payload: ChallengeCreate, request: Request, user=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        for field, value in payload.model_dump().items():
            setattr(challenge, field, value)
        await write_audit(session, user.id, "challenge.update", "challenge", str(challenge.id), {"code": code})
        await session.commit()
        await session.refresh(challenge, attribute_names=["flags"])
        return challenge_view(challenge, include_flags=True)


@app.delete("/api/v1/challenges/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_challenge(code: str, request: Request, user=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        challenge.is_published = False
        await write_audit(session, user.id, "challenge.archive", "challenge", str(challenge.id), {"code": code})
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/v1/challenges/{code}/flags", response_model=ChallengeView)
async def create_flag(code: str, payload: FlagCreate, request: Request, user=Depends(require_roles("admin", "instructor"))):
    if payload.mode == "static" and not payload.value:
        raise HTTPException(status_code=422, detail="Una flag estática requiere un valor")
    if payload.mode == "dynamic" and not payload.template:
        raise HTTPException(status_code=422, detail="Una flag dinámica requiere una plantilla")
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        flag = ChallengeFlag(
            challenge_id=challenge.id,
            label=payload.label,
            flag_hash=hash_password(payload.value) if payload.mode == "static" and payload.value else None,
            flag_order=payload.flag_order,
            is_active=True,
            mode=payload.mode,
            template=payload.template if payload.mode == "dynamic" else None,
        )
        session.add(flag)
        await write_audit(session, user.id, "flag.create", "challenge", str(challenge.id), {"order": payload.flag_order, "mode": payload.mode})
        await session.commit()
        await session.refresh(challenge, attribute_names=["flags"])
        return challenge_view(challenge, include_flags=True)


@app.put("/api/v1/challenges/{code}/flags/{flag_id}", response_model=ChallengeView)
async def update_flag(code: str, flag_id: int, payload: FlagUpdate, request: Request, user=Depends(require_roles("admin", "instructor"))):
    if payload.mode == "static" and payload.value == "":
        raise HTTPException(status_code=422, detail="Una flag estática requiere un valor")
    if payload.mode == "dynamic" and not payload.template:
        raise HTTPException(status_code=422, detail="Una flag dinámica requiere una plantilla")
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        flag = next((item for item in challenge.flags if item.id == flag_id), None)
        if flag is None:
            raise HTTPException(status_code=404, detail="Flag no encontrada")
        flag.label = payload.label
        flag.flag_order = payload.flag_order
        flag.is_active = payload.is_active
        flag.mode = payload.mode
        flag.template = payload.template if payload.mode == "dynamic" else None
        if payload.mode == "static" and payload.value is not None:
            flag.flag_hash = hash_password(payload.value)
        elif payload.mode == "dynamic":
            flag.flag_hash = None
            # Old per-run values must not survive a mode switch.
            await session.execute(delete(ChallengeRunFlag).where(ChallengeRunFlag.flag_id == flag.id))
        await write_audit(session, user.id, "flag.update", "flag", str(flag.id), {"challenge": code, "order": payload.flag_order, "mode": payload.mode, "active": payload.is_active})
        await session.commit()
        await session.refresh(challenge, attribute_names=["flags"])
        return challenge_view(challenge, include_flags=True)


@app.delete("/api/v1/challenges/{code}/flags/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(code: str, flag_id: int, request: Request, user=Depends(require_roles("admin", "instructor"))):
    async with request.app.state.session_factory() as session:
        challenge = await session.scalar(select(Challenge).where(Challenge.code == code))
        if challenge is None:
            raise HTTPException(status_code=404, detail="Reto no encontrado")
        flag = await session.get(ChallengeFlag, flag_id)
        if flag is None or flag.challenge_id != challenge.id:
            raise HTTPException(status_code=404, detail="Flag no encontrada")
        await write_audit(session, user.id, "flag.delete", "flag", str(flag.id), {"challenge": code})
        await session.delete(flag)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def render_dynamic_flag(template: str, *, code: str, username: str, run_id: int) -> str:
    # Cleartext is generated only for the current run. Only its hash is persisted.
    value = template
    value = value.replace("{{CODE}}", code)
    value = value.replace("{{USER}}", username)
    value = value.replace("{{RUN_ID}}", str(run_id))
    value = value.replace("{{RAND}}", secrets.token_hex(8))
    return value


# ============================================================
# EJECUCIÓN Y VALIDACIÓN DE RETOS
# ============================================================

def _asset_ref_key(value: str) -> str:
    return value.strip().upper()


async def _sync_player_guacamole_permissions(request: Request, user_id: int) -> None:
    """Concede a un jugador solo las conexiones Guacamole de los retos de sus grupos."""
    async with request.app.state.session_factory() as session:
        user = await session.get(User, user_id)
        if user is None or user.role != "player":
            return

        assigned_challenges = (
            await session.scalars(
                select(Challenge)
                .join(ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == Challenge.id)
                .join(GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id)
                .join(StudentGroup, StudentGroup.id == GroupMembership.group_id)
                .where(GroupMembership.user_id == user_id, StudentGroup.is_active.is_(True))
            )
        ).unique().all()

        vms = (await session.scalars(select(VMAsset))).all()
        refs_to_connections: dict[str, str] = {}
        for vm in vms:
            if vm.guacamole_connection_id:
                refs_to_connections[_asset_ref_key(vm.name)] = vm.guacamole_connection_id
                if vm.ip_address:
                    refs_to_connections[_asset_ref_key(vm.ip_address)] = vm.guacamole_connection_id

        lab_rows = (await session.scalars(select(Laboratory))).all()
        labs_by_key: dict[str, int] = {}
        for lab in lab_rows:
            labs_by_key[_asset_ref_key(lab.name)] = lab.id
            if lab.code:
                labs_by_key[_asset_ref_key(lab.code)] = lab.id

        lab_vms = (await session.scalars(select(VMAsset))).all()
        vm_by_lab: dict[int, list[VMAsset]] = {}
        for vm in lab_vms:
            vm_by_lab.setdefault(vm.laboratory_id, []).append(vm)

        desired: dict[str, list[str]] = {}
        for challenge in assigned_challenges:
            for raw_ref in challenge.asset_references or []:
                key = _asset_ref_key(raw_ref)
                direct = refs_to_connections.get(key)
                if direct:
                    desired[direct] = ["READ"]
                    continue
                lab_id = labs_by_key.get(key)
                if lab_id:
                    for vm in vm_by_lab.get(lab_id, []):
                        if vm.guacamole_connection_id:
                            desired[vm.guacamole_connection_id] = ["READ"]

    try:
        await request.app.state.guacamole_admin.patch_user_permissions(
            user.username,
            system_permissions=[],
            connection_permissions=desired,
        )
    except GuacamoleApiError as exc:
        if exc.status_code != 404:
            raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar los permisos de Guacamole: {exc.detail or exc}") from exc


async def _sync_guacamole_group_permissions(request: Request, group_id: int) -> None:
    """Sincroniza un grupo académico con un user group real de Guacamole. Los permisos READ se heredan a sus miembros."""
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        if group is None:
            return
        if not group.guacamole_group_identifier:
            group.guacamole_group_identifier = group.code
            await session.commit()
        assigned_challenges = (await session.scalars(
            select(Challenge)
            .join(ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == Challenge.id)
            .where(ChallengeGroupAssignment.group_id == group_id)
        )).unique().all()
        vms = (await session.scalars(select(VMAsset))).all()
        refs_to_connections: dict[str, str] = {}
        for vm in vms:
            if vm.guacamole_connection_id:
                refs_to_connections[_asset_ref_key(vm.name)] = vm.guacamole_connection_id
                if vm.ip_address:
                    refs_to_connections[_asset_ref_key(vm.ip_address)] = vm.guacamole_connection_id
        labs = (await session.scalars(select(Laboratory))).all()
        labs_by_key = {_asset_ref_key(l.code or ""): l.id for l in labs if l.code}
        labs_by_key.update({_asset_ref_key(l.name): l.id for l in labs})
        vm_by_lab: dict[int, list[VMAsset]] = {}
        for vm in vms: vm_by_lab.setdefault(vm.laboratory_id, []).append(vm)
        desired: dict[str, list[str]] = {}
        for challenge in assigned_challenges:
            for raw_ref in challenge.asset_references or []:
                key = _asset_ref_key(raw_ref)
                direct = refs_to_connections.get(key)
                if direct: desired[direct] = ["READ"]; continue
                lab_id = labs_by_key.get(key)
                if lab_id:
                    for vm in vm_by_lab.get(lab_id, []):
                        if vm.guacamole_connection_id: desired[vm.guacamole_connection_id] = ["READ"]
        guac_identifier = group.guacamole_group_identifier
    try:
        try:
            await request.app.state.guacamole_admin.get_user_group_permissions(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code == 404:
                await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=False)
            else: raise
        await request.app.state.guacamole_admin.patch_user_group_permissions(guac_identifier, connection_permissions=desired)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar permisos del grupo con Guacamole: {exc.detail or exc}") from exc


async def _sync_group_members_guacamole_permissions(request: Request, group_id: int) -> None:
    async with request.app.state.session_factory() as session:
        user_ids = list((await session.scalars(select(GroupMembership.user_id).where(GroupMembership.group_id == group_id))).all())
    for user_id in user_ids:
        await _sync_player_guacamole_permissions(request, int(user_id))


async def _find_challenge_vm(session, challenge: Challenge):
    """Busca una VM lista y asociada al reto mediante asset_references."""
    refs = {_asset_ref_key(value) for value in (challenge.asset_references or []) if value.strip()}
    if not refs:
        return None, None

    labs = (
        await session.scalars(
            select(Laboratory)
            .options(selectinload(Laboratory.vms))
            .where(Laboratory.status.in_(("ready", "planned")))
            .order_by(Laboratory.id)
        )
    ).unique().all()

    for lab in labs:
        lab_keys = {_asset_ref_key(lab.code or ""), _asset_ref_key(lab.name)}
        for vm in lab.vms:
            vm_keys = {_asset_ref_key(vm.name)} | lab_keys
            if refs.intersection(vm_keys) and vm.status == "ready" and vm.guacamole_connection_id:
                return lab, vm
    return None, None


@app.post("/api/v1/challenges/{code}/start", response_model=RunView)
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


@app.get("/api/v1/runs", response_model=list[RunView])
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


@app.post("/api/v1/runs/{run_id}/close", response_model=RunView)
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


@app.post("/api/v1/challenges/{code}/submissions", response_model=SubmissionResponse)
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


# ============================================================
# RANKING, REPORTES Y TIEMPO REAL
# ============================================================

@app.get("/api/v1/reports/progress")
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


@app.get("/api/v1/ranking", response_model=RankingResponse)
async def ranking(request: Request, user=Depends(get_current_user)):
    return RankingResponse(rows=[RankingRow(**row) for row in await ranking_rows(request.app.state.session_factory)])


@app.get("/api/v1/reports/ranking.csv", response_class=Response)
async def export_ranking_csv(request: Request, _=Depends(require_roles("admin", "instructor"))):
    rows = await ranking_rows(request.app.state.session_factory)
    lines = ["position,username,total_points,challenges_completed"]
    for row in rows:
        # Los nombres de usuario no permiten comas al crearse, pero se protegen de todas formas para CSV.
        lines.append(f'{row["position"]},"{row["username"].replace(chr(34), chr(34) * 2)}",{row["total_points"]},{row["challenges_completed"]}')
    return Response("\n".join(lines) + "\n", media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ranking.csv"})


@app.get("/api/v1/progress")
async def progress(request: Request, user=Depends(require_roles("player"))):
    async with request.app.state.session_factory() as session:
        completed = (await session.scalars(select(ChallengeCompletion).where(ChallengeCompletion.user_id == user.id))).all()
        total = sum(item.awarded_points for item in completed)
        return {"total_points": total, "challenges_completed": len(completed)}


@app.websocket("/api/v1/ws/ranking")
async def ranking_socket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        if not token:
            raise ValueError("missing")
        decode_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await app.state.sockets.connect(websocket)
    await websocket.send_json({"type": "ranking.updated", "rows": await ranking_rows(app.state.session_factory)})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        app.state.sockets.disconnect(websocket)


# ============================================================
# MANEJO CENTRALIZADO DE ERRORES
# ============================================================

@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "La operación entra en conflicto con datos existentes"})
