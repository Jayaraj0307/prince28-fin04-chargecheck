
"""Database operations for background ingestion jobs."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chargecheck.db.models import IngestItem, IngestJob


class IngestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def known_ids(self) -> set[str]:
        result = await self.session.execute(
            select(IngestItem.record["url"].as_string())
        )
        return {value for value in result.scalars() if value}

    async def create(self, records: list[dict]) -> str:
        import uuid

        job_id = uuid.uuid4().hex
        job = IngestJob(id=job_id, requested=len(records))
        self.session.add(job)

        for record in records:
            self.session.add(
                IngestItem(job_id=job_id, record=record)
            )

        await self.session.commit()
        return job_id

    async def progress(self, job_id: str) -> dict:
        result = await self.session.execute(
            select(IngestItem.status, func.count(IngestItem.id))
            .where(IngestItem.job_id == job_id)
            .group_by(IngestItem.status)
        )
        counts = dict(result.all())

        job = await self.session.get(IngestJob, job_id)
        if job is None:
            return {}

        return {
            "job_id": job_id,
            "requested": job.requested,
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "done": counts.get("done", 0),
            "skipped": counts.get("skipped", 0),
            "failed": counts.get("failed", 0),
        }

    async def dead_letter(self, limit: int = 100) -> list[dict]:
        result = await self.session.execute(
            select(IngestItem)
            .where(IngestItem.status == "failed")
            .order_by(IngestItem.updated_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": item.id,
                "job_id": item.job_id,
                "record": item.record,
                "attempts": item.attempts,
                "error": item.error,
            }
            for item in result.scalars()
        ]

    async def failed_records(self) -> list[dict]:
        result = await self.session.execute(
            select(IngestItem.record).where(IngestItem.status == "failed")
        )
        return list(result.scalars())

    async def open_item_ids(self) -> list[int]:
        result = await self.session.execute(
            select(IngestItem.id).where(
                IngestItem.status.in_(["queued", "running"])
            )
        )
        return list(result.scalars())
