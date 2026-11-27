"""Background worker for downloading, parsing, storing and extracting documents."""

import asyncio
import hashlib
from pathlib import Path
from time import monotonic

from arq import Retry
from sqlalchemy import select

from chargecheck.db.models import Document, IngestItem
from chargecheck.ingest.fetch import Manifest, Source, fetch_one
from chargecheck.ingest.parse import ParseError, parse_file
from chargecheck.ingest.store import document_id, save_document, save_failure
from chargecheck.llm.extract import DocMeta, document_text, extract, save

PROMPT_VERSION = "extract_v1"


async def ingest_document(ctx: dict, item_id: int) -> None:
    """Process one queued ingestion item."""
    async with ctx["sessionmaker"]() as session:
        item = await session.get(IngestItem, item_id)

        if item is None or item.status in {"done", "skipped", "failed"}:
            return

        item.status = "running"
        item.attempts += 1
        item.error = ""
        await session.commit()

        record = dict(item.record or {})

        try:
            path_value = record.get("path")
            path = Path(path_value) if path_value else None

            # Download remote files when no usable local file exists.
            if path is None or not path.is_file():
                url = record.get("url")

                if not url:
                    item.status = "failed"
                    item.error = "No local file or source URL supplied."
                    await session.commit()
                    return

                source = Source(
                    url=url,
                    source=record.get("source", "manual"),
                    licence=record.get("licence", ""),
                    title=record.get("title", ""),
                )

                result = await fetch_one(
                    ctx["client"],
                    source,
                    root=Path("."),
                    raw_dir=Path("data/raw"),
                    robots=ctx["robots"],
                    gate=ctx["host_gate"],
                    slots=ctx["download_slots"],
                    max_attempts=4,
                    sleep=asyncio.sleep,
                )

                if result.get("status") == "blocked":
                    item.status = "failed"
                    item.error = "Download blocked by robots.txt."
                    await session.commit()
                    return

                if result.get("status") != "downloaded":
                    raise RuntimeError(result.get("error", "Document download failed."))

                record.update(result)
                path = Path(record["path"])
                item.record = record
                await session.commit()

                Manifest(Path(ctx["settings"].manifest_file)).add(record)

            if not path.is_file():
                raise FileNotFoundError(f"Downloaded file not found: {path}")

            # Calculate the content hash if it is missing.
            if not record.get("sha256"):
                record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

            record["path"] = str(path)
            external_id = document_id(record["sha256"])

            existing = await session.scalar(
                select(Document).where(Document.external_id == external_id)
            )

            if existing is None:
                parsed = await asyncio.to_thread(parse_file, path)
                await save_document(session, record, parsed)

                existing = await session.scalar(
                    select(Document).where(Document.external_id == external_id)
                )

            # Extract metadata for parsed documents, not legacy records.
            if existing is not None and existing.doc_type != "record":
                metadata = existing.metadata_ or {}
                extraction_info = metadata.get("extract", {})

                if extraction_info.get("prompt") != PROMPT_VERSION:
                    text = await document_text(
                        session,
                        existing,
                        chars=6000,
                    )

                    # Apply a shared requests-per-minute limit.
                    async with ctx["pace_lock"]:
                        interval = 60 / max(
                            1,
                            ctx["settings"].ingest_rpm,
                        )
                        elapsed = monotonic() - ctx["last_llm_call"]

                        if elapsed < interval:
                            await asyncio.sleep(interval - elapsed)

                        result = await extract(
                            ctx["gateway"],
                            DocMeta,
                            ctx["prompt"],
                            PROMPT_VERSION,
                            existing.title,
                            text,
                        )

                        ctx["last_llm_call"] = monotonic()

                    await save(
                        session,
                        existing,
                        result,
                        PROMPT_VERSION,
                    )

            item.status = "done"
            item.pages = (existing.metadata_ or {}).get("pages", 0) if existing is not None else 0
            item.error = ""
            await session.commit()

        except ParseError as exc:
            await save_failure(session, record, exc)
            item.status = "failed"
            item.error = str(exc)[:2000]
            await session.commit()

        except Exception as exc:
            item.error = str(exc)[:2000]
            settings = ctx["settings"]

            if item.attempts < settings.ingest_max_tries:
                item.status = "queued"
                await session.commit()
                raise Retry(defer=30 * item.attempts) from exc

            item.status = "failed"
            await session.commit()
