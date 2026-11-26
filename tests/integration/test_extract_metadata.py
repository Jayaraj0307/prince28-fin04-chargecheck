"""Metadata extraction persistence against PostgreSQL."""

import pytest
from sqlalchemy import select

from chargecheck.db.models import Document
from chargecheck.llm.extract import DocMeta, Extraction, save


@pytest.mark.asyncio
async def test_extraction_metadata_is_saved_without_overwriting_parser_metadata(
    database_url,
):
    from chargecheck.config import Settings
    from chargecheck.db.session import make_engine, make_sessionmaker

    engine = make_engine(Settings(app_env="ci", database_url=database_url, _env_file=None))
    sessionmaker = make_sessionmaker(engine)

    external_id = "integration-extract-test"
    try:
        async with sessionmaker() as session:
            document = Document(
                external_id=external_id,
                title="Integration test document",
                source_url="https://example.org/test",
                licence="CC BY 4.0",
                doc_type="pdf",
                sha256="cd" * 32,
                metadata_={"source": "Test Bank", "pages": 2},
            )
            session.add(document)
            await session.flush()

            result = Extraction(
                record=DocMeta(
                    doc_kind="list",
                    year=2026,
                    language="en",
                    summary="A test document describing banking service charges.",
                    topics=["service charges"],
                    bank=["Test Bank"],
                    charge_type=["atm fee"],
                    account_variant=["savings"],
                    effective_from=[],
                ),
                attempts=1,
                model="test-model",
            )

            await save(session, document, result, "extract_v1")

            saved = await session.scalar(
                select(Document).where(Document.external_id == external_id)
            )
            assert saved is not None
            assert saved.metadata_["source"] == "Test Bank"
            assert saved.metadata_["pages"] == 2
            assert saved.metadata_["doc_kind"] == "list"
            assert saved.metadata_["bank"] == ["Test Bank"]
            assert saved.metadata_["extract"]["prompt"] == "extract_v1"
    finally:
        async with sessionmaker() as session:
            document = await session.scalar(
                select(Document).where(Document.external_id == external_id)
            )
            if document is not None:
                await session.delete(document)
                await session.commit()
        await engine.dispose()
