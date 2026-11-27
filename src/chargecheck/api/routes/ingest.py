
"""API endpoints for background document ingestion."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chargecheck.config import get_settings
from chargecheck.db.ingest_jobs import IngestRepository
from chargecheck.db.models import IngestItem
from chargecheck.db.session import get_session
from chargecheck.workers.queue import Queue

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestRequest(BaseModel):
    records: list[dict] = Field(min_length=1)


def require_admin(x_admin_token: str = Header(default="")) -> None:
    settings = get_settings()

    if not settings.admin_token:
        if settings.app_env == "local":
            return
        raise HTTPException(status_code=401, detail="Admin token is not configured")

    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("", status_code=202, dependencies=[Depends(require_admin)])
async def start_ingestion(
    body: IngestRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    repository = IngestRepository(session)
    job_id = await repository.create(body.records)

    item_ids = list(
        await session.scalars(
            select(IngestItem.id).where(IngestItem.job_id == job_id)
        )
    )

    queue = await Queue.connect()
    try:
        await queue.put(item_ids)
    finally:
        await queue.close()

    return {
        "job_id": job_id,
        "status": "queued",
        "requested": len(body.records),
    }


@router.get("/dead-letter", dependencies=[Depends(require_admin)])
async def dead_letter(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await IngestRepository(session).dead_letter(limit=limit)


@router.get("/{job_id}")
async def ingestion_progress(
    job_id: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    progress = await IngestRepository(session).progress(job_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    return progress
