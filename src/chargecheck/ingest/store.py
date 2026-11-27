"""Save parsed documents and pages, or record parsing failures."""

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from chargecheck.db.models import Document, Page, ParseFailure
from chargecheck.ingest.parse import ParsedDoc, ParseError


def document_id(sha256: str) -> str:
    """Files are identified by their content: identical bytes are one document."""
    return f"f-{sha256[:20]}"


async def parsed_ids(session: AsyncSession) -> set[str]:
    """Return IDs of documents that have been parsed."""
    rows = await session.scalars(select(Document.external_id).where(Document.doc_type != "record"))
    return set(rows)


async def failed_paths(session: AsyncSession) -> set[str]:
    """Return paths of files recorded as parsing failures."""
    return set(await session.scalars(select(ParseFailure.path)))


async def save_document(
    session: AsyncSession,
    record: dict,
    parsed: ParsedDoc,
) -> None:
    """
    Save one parsed document and its pages.

    PostgreSQL handles concurrent inserts of identical documents safely.
    Only the worker that successfully inserts the document inserts its pages.
    """
    title = parsed.title or record.get("title") or Path(record["path"]).stem

    external_id = document_id(record["sha256"])

    metadata = {
        "source": record["source"],
        "path": record["path"],
        "parser": parsed.parser,
        "pages": len(parsed.pages),
        "tables": sum(page.tables for page in parsed.pages),
        "chars": sum(len(page.text) for page in parsed.pages),
    }

    # Insert the document only if another worker has not already inserted it.
    statement = (
        insert(Document)
        .values(
            external_id=external_id,
            title=title[:500],
            source_url=record["url"],
            licence=(record.get("licence") or "")[:200],
            doc_type=parsed.kind,
            sha256=record["sha256"],
            metadata_=metadata,
        )
        .on_conflict_do_nothing(
            index_elements=[Document.external_id],
        )
        .returning(Document.id)
    )

    result = await session.execute(statement)
    new_document_id = result.scalar_one_or_none()

    if new_document_id is not None:
        # Only the worker that created the document inserts its pages.
        session.add_all(
            [
                Page(
                    document_id=new_document_id,
                    page_no=page.page_no,
                    text=page.text,
                    headings=page.headings,
                )
                for page in parsed.pages
            ]
        )

    # Remove an old parsing failure for this file.
    await session.execute(delete(ParseFailure).where(ParseFailure.path == record["path"]))

    # Document, pages and failure cleanup commit together.
    await session.commit()


async def save_failure(
    session: AsyncSession,
    record: dict,
    error: ParseError,
) -> None:
    """Insert a parsing failure or increment its attempt count."""
    row = {
        "path": record["path"],
        "sha256": record["sha256"],
        "source_url": record["url"],
        "reason": error.reason,
        "detail": error.detail,
    }

    statement = insert(ParseFailure).values(**row)

    statement = statement.on_conflict_do_update(
        index_elements=[ParseFailure.path],
        set_={
            "reason": error.reason,
            "detail": error.detail,
            "attempts": ParseFailure.attempts + 1,
        },
    )

    await session.execute(statement)
    await session.commit()
