"""ARQ worker startup and shutdown configuration."""

import asyncio

from arq.connections import RedisSettings

from chargecheck.config import get_settings
from chargecheck.db.ingest_jobs import IngestRepository
from chargecheck.db.session import make_engine, make_sessionmaker
from chargecheck.ingest.fetch import HostGate, Robots, make_client
from chargecheck.llm.gateway import build_gateway
from chargecheck.workers.ingest import ingest_document


async def startup(ctx: dict) -> None:
    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required by the worker")

    engine = make_engine(settings)
    sessionmaker = make_sessionmaker(engine)
    client = make_client(max_concurrency=settings.ingest_concurrency)
    gateway = build_gateway(settings)

    prompt_path = settings.prompts_dir / "extract_v1.md"
    prompt = prompt_path.read_text(encoding="utf-8")

    ctx.update(
        settings=settings,
        engine=engine,
        sessionmaker=sessionmaker,
        client=client,
        robots=Robots(client),
        host_gate=HostGate(
            delay=0.5,
            sleep=asyncio.sleep,
        ),
        download_slots=asyncio.Semaphore(settings.ingest_concurrency),
        gateway=gateway,
        prompt=prompt,
        pace_lock=asyncio.Lock(),
        last_llm_call=0.0,
    )

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
    client = ctx.get("client")

    if client is not None:
        await client.aclose()

    gateway = ctx.get("gateway")

    if gateway is not None:
        for provider in gateway.providers:
            await provider.close()

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
