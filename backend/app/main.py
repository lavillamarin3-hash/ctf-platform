"""Punto de entrada FastAPI.

La aplicación solo compone middlewares, ciclo de vida y routers.
La lógica funcional vive en servicios y módulos de API separados.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .core import get_settings
from .services.bootstrap import lifespan
from .api.auth import router as auth_router
from .api.users import router as users_router
from .api.guacamole import router as guacamole_router
from .api.groups import router as groups_router
from .api.laboratories import router as laboratories_router
from .api.challenges import router as challenges_router
from .api.runs import router as runs_router
from .api.reports import router as reports_router

# Configuración central de la API. Los routers se registran abajo por contexto.
app = FastAPI(title="Plataforma CTF del laboratorio", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().public_origin, "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Orden del registro: salud/auth → administración → contenido/inventario → ejecución → reportes.
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(guacamole_router)
app.include_router(groups_router)
app.include_router(laboratories_router)
app.include_router(challenges_router)
app.include_router(runs_router)
app.include_router(reports_router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError):
    """Devuelve un conflicto legible cuando PostgreSQL rechaza una restricción."""
    return JSONResponse(status_code=409, content={"detail": "La operación entra en conflicto con datos existentes."})
