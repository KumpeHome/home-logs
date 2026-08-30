from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401
from app.api.routers.core import router as core_router
from app.api.routers.domain import logs_router, members_router, more_router
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.schema import ensure_schema
from app.db.session import engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    if getattr(application.state, "init_db", True):
        ensure_schema(engine)
    yield
    if getattr(application.state, "init_db", True):
        engine.dispose()


def create_app(*, init_db: bool = True) -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.state.init_db = init_db
    origins = [
        item.strip() for item in settings.cors_origins.split(",") if item.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}
        )

    application.include_router(core_router, prefix="/api")
    application.include_router(members_router, prefix="/api")
    application.include_router(logs_router, prefix="/api")
    application.include_router(more_router, prefix="/api")
    return application


app = create_app()
