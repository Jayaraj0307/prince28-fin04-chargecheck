"""Database recording and usage reporting for LLM calls."""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from chargecheck.db.models import LlmCall


def make_recorder(session_factory: async_sessionmaker[AsyncSession]):
    """Return an async callback that records each LLM call."""

    async def record(values: dict) -> None:
        async with session_factory() as session:
            session.add(LlmCall(**values))
            await session.commit()

    return record


class UsageRepository:
    """Read daily LLM usage totals from the database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_day(self, days: int = 30) -> list[dict]:
        """Return call count, tokens, and INR cost grouped by day."""

        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)

        day_column = func.date(LlmCall.created_at).label("day")
        statement = (
            select(
                day_column,
                func.count(LlmCall.id).label("calls"),
                func.sum(LlmCall.tokens_in).label("tokens_in"),
                func.sum(LlmCall.tokens_out).label("tokens_out"),
                func.sum(LlmCall.cost_inr).label("cost_inr"),
            )
            .where(LlmCall.created_at >= datetime.combine(start, time.min, tzinfo=UTC))
            .group_by(day_column)
            .order_by(day_column)
        )

        result = await self.session.execute(statement)
        return [
            {
                "day": str(row.day),
                "calls": row.calls,
                "tokens_in": row.tokens_in or 0,
                "tokens_out": row.tokens_out or 0,
                "cost_inr": float(row.cost_inr or 0),
            }
            for row in result
        ]
