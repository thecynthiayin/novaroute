import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api import activity, applications, auth, internships, profiles, simple_rag, trust
from app.core.body_limit import UploadBodyLimit
from app.core.config import settings
from app.db.session import engine
from app.services.embeddings import EmbeddingUnavailable, embeddings


@asynccontextmanager
async def lifespan(app):
    if settings().embedding_load_on_start:
        try:
            await run_in_threadpool(embeddings.load)
        except EmbeddingUnavailable:
            logging.getLogger(__name__).warning("Embedding model unavailable at startup")
    yield
    engine.dispose()


def create_app():
    app = FastAPI(title="NovaRoute API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(UploadBodyLimit, max_bytes=settings().upload_max_bytes + 65536)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings().origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def headers(request: Request, call_next):
        if request.url.path == "/api/upload-resume":
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > settings().upload_max_bytes + 65536:
                return JSONResponse({"detail": "Upload exceeds size limit"}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse(
            {"detail": "This record conflicts with existing data. Reload and try again."}, status_code=409
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        logging.getLogger(__name__).error("Database operation failed: %s", type(exc).__name__)
        return JSONResponse(
            {"detail": "Database unavailable. Check local services and migrations."}, status_code=503
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Omit Pydantic's input field; it may include passwords or resume content.
        return JSONResponse(
            {"detail": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]},
            status_code=422,
        )

    for router in (
        auth.router,
        profiles.router,
        trust.router,
        internships.router,
        applications.router,
        activity.router,
        simple_rag.router,
    ):
        app.include_router(router, prefix="/api")

    @app.get("/api/health", tags=["Health"])
    def health() -> dict:
        return {"status": "ok", "ai_mode": settings().ai_mode, "environment": settings().environment}

    @app.get("/api/ready", tags=["Health"])
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.execute(text("SELECT version_num FROM alembic_version"))
            database = "ready"
        except SQLAlchemyError:
            database = "unavailable_or_unmigrated"
        return JSONResponse(
            {"database": database, "model": embeddings.state, "ai_mode": settings().ai_mode},
            status_code=200 if database == "ready" else 503,
        )

    return app


app = create_app()
