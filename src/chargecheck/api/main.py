"""App factory: build a fully wired FastAPI app from settings."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chargecheck.api.errors import register_error_handlers
from chargecheck.api.middleware import request_context
from chargecheck.api.routes import documents, health
from chargecheck.config import Settings, get_settings
from chargecheck.db.session import close_db
from chargecheck.logging_setup import setup_logging

logger = logging.getLogger("chargecheck")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("ChargeCheck application starting")

        try:
            yield
        finally:
            await close_db()
            logger.info("ChargeCheck application stopped")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.settings = settings

    app.middleware("http")(request_context)
    register_error_handlers(app)

    app.include_router(health.router)

    from fastapi import APIRouter

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    app.include_router(v1)

    return app
