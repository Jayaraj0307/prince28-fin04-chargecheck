"""Health and readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from chargecheck.api.deps import SettingsDep, check_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/ready")
async def ready(
    response: Response,
    db_ready: Annotated[bool, Depends(check_db)],
) -> dict:
    if not db_ready:
        response.status_code = 503
        return {"status": "not_ready", "checks": {"database": False}}

    return {"status": "ready", "checks": {"database": True}}
