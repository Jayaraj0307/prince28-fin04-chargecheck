"""ARQ worker startup and shutdown configuration."""

from arq.connections import RedisSettings

from chargecheck.config import get_settings
from chargecheck.db.ingest_jobs import IngestRepository
from chargecheck.db.session import make_engine, make_sessionmaker
from chargecheck.workers.ingest import ingest_document


async def startup(ctx: dict) -> None:
    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required by the worker")

    engine = make_engine(settings)
    sessionmaker = make_sessionmaker(engine)

    ctx["settings"] = settings
    ctx["engine"] = engine
    ctx["sessionmaker"] = sessionmaker

    # Requeue unfinished items after a worker restart.
    async with sessionmaker() as session:
        repository = IngestRepository(session)
        item_ids = await repository.open_item_ids()

    for item_id in item_ids:
        await ctx["redis"].enqueue_job(
            "ingest_document",
            item_id,
            _job_id=f"ingest:{item_id}",
        )


async def shutdown(ctx: dict) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


class WorkerSettings:
    functions = [ingest_document]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = get_settings().ingest_concurrency
    job_timeout = get_settings().ingest_job_timeout
    max_tries = get_settings().ingest_max_tries
    keep_result = 0
