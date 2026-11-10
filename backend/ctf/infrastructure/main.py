"""Arranque HTTP sin tareas periódicas ni creación automática de esquema."""
from contextlib import asynccontextmanager
import asyncio
import logging
import secrets
from time import monotonic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from redis.exceptions import RedisError
from .runtime import Runtime
from ..application.admin import bootstrap
from ..domain.laboratory import DomainError, RecursoNoDisponibleError, CorridaYaActivaError
from ..adapters.http import auth, routes, terminal, realtime, guacamole_admin
from ..adapters.persistence.repository import audit


@asynccontextmanager
async def lifespan(app):
    runtime = Runtime()
    app.state.runtime = runtime
    app.state.health_open_until = 0
    try:
        await bootstrap(runtime.repo, runtime.settings)
        yield
    finally: await runtime.close()


app = FastAPI(title="CoCiber CTF", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(auth.router)
app.include_router(routes.router)
app.include_router(terminal.router)
app.include_router(realtime.router)
app.include_router(guacamole_admin.router)


@app.middleware("http")
async def correlation(request, call_next):
    request.state.correlation_id = secrets.token_hex(16)
    try:
        runtime = getattr(request.app.state, "runtime", None)
        if runtime and hasattr(runtime, "availability") and request.url.path.startswith("/api/v1/") and not request.url.path.startswith("/api/v1/health"):
            await runtime.availability.check()
        response = await call_next(request)
    except Exception:
        response = await error_response(request, 503, "SERVICE_UNAVAILABLE", "No se pudo completar la operación. Reintenta más tarde.")
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["Cache-Control"] = "no-store"
    return response


async def error_response(request, status, code, message):
    correlation_id = getattr(request.state, "correlation_id", secrets.token_hex(16))
    runtime = getattr(request.app.state, "runtime", None)
    if runtime:
        try:
            async with asyncio.timeout(2):
                async with runtime.repo.sessions.begin() as s:
                    audit(s, "http.error", correlation_id, getattr(request.state, "user_id", None), error_code=code, status=status)
        except Exception:
            logging.warning("Auditoría pendiente correlation_id=%s code=%s", correlation_id, code)
    return JSONResponse(status_code=status, content={"error_code": code, "message": message, "correlation_id": correlation_id})


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc):
    return await error_response(request, exc.status_code, f"HTTP_{exc.status_code}", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation(request: Request, exc):
    return await error_response(request, 422, "VALIDATION_ERROR", "Revisa los campos del formulario.")


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc):
    status = 503 if isinstance(exc, RecursoNoDisponibleError) else 409 if isinstance(exc, CorridaYaActivaError) else 422
    return await error_response(request, status, exc.code, exc.message)


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc):
    return await error_response(request, 409, "DATA_CONFLICT", "Los datos ya existen o un recurso está reservado.")


@app.exception_handler(SQLAlchemyError)
@app.exception_handler(RedisError)
async def dependency_error(request: Request, exc):
    return await error_response(request, 503, "DEPENDENCY_UNAVAILABLE", "Una dependencia no está disponible. Reintenta más tarde.")


@app.get("/api/v1/health")
async def health(): return {"status": "ok", "service": "ctf-api", "schema": "fresh"}


@app.get("/api/v1/health/ready")
async def ready(request: Request):
    runtime = request.app.state.runtime
    try:
        checks = await runtime.availability.check()
        status = 200
    except RecursoNoDisponibleError:
        checks, status = runtime.availability.status, 503
    return JSONResponse(status_code=status, content={"app": "alive", **checks})
