"""ARQ Redis queue wrapper."""

from arq import create_pool
from arq.connections import RedisSettings

from chargecheck.config import get_settings

JOB = "ingest_document"


class Queue:
    def __init__(self, pool):
        self.pool = pool

    @classmethod
    async def connect(cls):
        settings = get_settings()
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        pool = await create_pool(redis_settings)
        return cls(pool)

    async def put(self, item_ids: list[int]) -> None:
        for item_id in item_ids:
            await self.pool.enqueue_job(
                JOB,
                item_id,
                _job_id=f"ingest:{item_id}",
            )

    async def close(self) -> None:
        await self.pool.aclose()
