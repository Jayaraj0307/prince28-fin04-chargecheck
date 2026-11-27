"""App factory: build a fully wired FastAPI app from settings."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from chargecheck.api.errors import register_error_handlers
from chargecheck.api.middleware import request_context
from chargecheck.api.routes import chat, documents, health, ingest
from chargecheck.config import Settings, get_settings
from chargecheck.db.llm_calls import make_recorder
from chargecheck.db.session import SessionLocal, close_db
from chargecheck.llm.gateway import build_gateway
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
            for provider in app.state.gateway.providers:
                await provider.close()
            await close_db()
            logger.info("ChargeCheck application stopped")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    recorder = make_recorder(SessionLocal) if SessionLocal is not None else None
    app.state.settings = settings
    app.state.gateway = build_gateway(settings, recorder)
    app.state.system_prompt = (settings.prompts_dir / "chat_system_v1.md").read_text(
        encoding="utf-8"
    )

    app.middleware("http")(request_context)
    register_error_handlers(app)

    app.include_router(health.router)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    v1.include_router(chat.router)
    v1.include_router(ingest.router)
    app.include_router(v1)

    return app


app = create_app()
