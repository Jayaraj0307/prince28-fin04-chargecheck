from fastapi import APIRouter, FastAPI

from chargecheck.api.routes import documents
from chargecheck.config import Settings, get_settings
from chargecheck.logging_setup import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.state.settings = settings

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready():
        return {"status": "ready"}

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    app.include_router(v1)

    return app


app = create_app()
