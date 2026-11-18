"""Async PostgreSQL engine and session management."""

from collections.abc import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from chargecheck.config import Settings, get_settings


def make_engine(settings: Settings):
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required to connect to PostgreSQL")

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )


def make_sessionmaker(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


settings = get_settings()
engine = make_engine(settings) if settings.database_url else None
SessionLocal = make_sessionmaker(engine) if engine is not None else None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured",
        )

    async with SessionLocal() as session:
        yield session


async def close_db() -> None:
    if engine is not None:
        await engine.dispose()
