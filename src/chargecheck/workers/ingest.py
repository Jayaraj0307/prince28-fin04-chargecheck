
"""Background worker for processing ingestion items."""

import asyncio
from pathlib import Path

from arq import Retry
from sqlalchemy import select

from chargecheck.db.models import Document, IngestItem
from chargecheck.ingest.parse import ParseError, parse_file
from chargecheck.ingest.store import (
    document_id,
    save_document,
    save_failure,
)


async def ingest_document(ctx: dict, item_id: int) -> None:
    """Process one queued ingestion item."""
    sessionmaker = ctx["sessionmaker"]

    async with sessionmaker() as session:
        item = await session.get(IngestItem, item_id)

        if item is None:
            return

        if item.status in {"done", "skipped", "failed"}:
            return

        item.status = "running"
        item.attempts += 1
        item.error = ""
        await session.commit()

        record = item.record

        try:
            path = Path(record["path"])

            if not path.is_file():
                raise FileNotFoundError(f"File not found: {path}")

            async with session.begin():
                existing = await session.scalar(
                    select(Document).where(
                        Document.external_id == document_id(record["sha256"])
                    )
                )

            if existing is not None:
                item.status = "skipped"
                await session.commit()
                return

            parsed = await asyncio.to_thread(parse_file, path)

            await save_document(session, record, parsed)

            item.status = "done"
            item.pages = len(parsed.pages)
            item.error = ""
            await session.commit()

        except ParseError as exc:
            await save_failure(session, record, exc)
            item.status = "failed"
            item.error = str(exc)[:2000]
            await session.commit()

        except Exception as exc:
            item.error = str(exc)[:2000]

            settings = ctx.get("settings")
            max_tries = getattr(settings, "ingest_max_tries", 3)

            if item.attempts < max_tries:
                item.status = "queued"
                await session.commit()
                raise Retry(defer=30 * item.attempts) from exc

            item.status = "failed"
            await session.commit()


class WorkerSettings:
    functions = [ingest_document]
    max_jobs = 2
    job_timeout = 60
    max_tries = 3
    keep_result = 0
