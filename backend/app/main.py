import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import app.models  # noqa: F401
from app.api.routers.core import router as core_router
from app.api.routers.domain import logs_router, members_router, more_router
from app.api.routers.notifications import router as notifications_router
from app.brand import brand_file
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.schema import ensure_schema
from app.db.session import SessionLocal, engine
from app.notifications.channels import build_channels
from app.notifications.dispatch import dispatch_all

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    stop_poller = threading.Event()
    if getattr(application.state, "init_db", True):
        ensure_schema(engine)
        interval = get_settings().notification_poll_seconds
        if interval > 0:
            _start_poller(stop_poller, interval)
    yield
    stop_poller.set()
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
    application.include_router(notifications_router, prefix="/api")

    @application.api_route("/assets/brand/{filename}", methods=["GET", "HEAD"])
    def spa_brand_asset(filename: str) -> FileResponse:
        return brand_file(filename)

    @application.api_route("/favicon.ico", methods=["GET", "HEAD"])
    def favicon() -> FileResponse:
        return brand_file("logo.png")

    return application


def _start_poller(stop: threading.Event, interval: int) -> None:
    def loop() -> None:
        while not stop.wait(interval):
            db = SessionLocal()
            try:
                dispatch_all(db, build_channels(get_settings()))
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Notification reminders failed")
            finally:
                db.close()

    threading.Thread(target=loop, name="notification-poller", daemon=True).start()


app = create_app()
