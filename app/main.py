"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routes.health import router as health_router

APP_DIR = Path(__file__).resolve().parent


def configure_logging() -> None:
    """Set up structured JSON logging via structlog."""
    settings = get_settings()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    configure_logging()
    logger = structlog.get_logger()
    logger.info("application_startup", app_name=get_settings().APP_NAME)
    yield
    logger.info("application_shutdown")


templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_MAX_AGE,
    )

    # Static files
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    # Routers
    app.include_router(health_router)

    # Import and register app routers
    from app.auth.routes import router as auth_router
    from app.routes.api_keys import router as api_keys_router
    from app.routes.publications import router as publications_router
    from app.routes.reports import router as reports_router
    from app.routes.review import router as review_router
    from app.routes.sync import router as sync_router

    app.include_router(auth_router)
    app.include_router(api_keys_router)
    app.include_router(publications_router)
    app.include_router(review_router)
    app.include_router(reports_router)
    app.include_router(sync_router)

    # Root page
    @app.get("/")
    async def root(request: Request):
        from app.database import get_db
        from app.models.faculty import Faculty

        user = None
        user_id = request.session.get("user_id")
        if user_id:
            db = next(get_db())
            try:
                user = db.get(Faculty, user_id)
            finally:
                db.close()

        if user:
            return templates.TemplateResponse(
                request,
                "dashboard.html",
                {"user": user, "flash_messages": request.session.pop("flash_messages", [])},
            )
        return templates.TemplateResponse(
            request, "base.html", {"user": None, "flash_messages": []}
        )

    return app


app = create_app()
