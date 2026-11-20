"""Dependencies used by API endpoints."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chargecheck.config import Settings
from chargecheck.db.repository import DocumentRepository
from chargecheck.db.session import get_session
from chargecheck.store import RecordStore


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> RecordStore:
    return request.app.state.store


async def get_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRepository:
    return DocumentRepository(session)


async def check_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> bool:
    await session.execute(text("SELECT 1"))
    return True


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
StoreDep = Annotated[RecordStore, Depends(get_store)]
RepoDep = Annotated[DocumentRepository, Depends(get_repo)]
