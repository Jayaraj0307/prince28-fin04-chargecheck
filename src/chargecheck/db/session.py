"""Async PostgreSQL engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from chargecheck.config import Settings, get_settings


def make_engine(settings: Settings):
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        poolclass=__import__("sqlalchemy.pool", fromlist=["NullPool"]).NullPool,
    )


def make_sessionmaker(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


engine = make_engine(get_settings())
SessionLocal = make_sessionmaker(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def close_db() -> None:
    await engine.dispose()
