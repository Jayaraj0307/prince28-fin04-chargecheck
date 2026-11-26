"""PostgreSQL repository for ChargeCheck documents."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chargecheck.db.models import Document


class DocumentRepository:
    """Provides database operations for documents."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
        self,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
        doc_kind: str | None = None,
        language: str | None = None,
        bank: str | None = None,
        charge_type: str | None = None,
    ) -> list[Document]:
        statement = select(Document)

        if q:
            statement = statement.where(Document.title.ilike(f"%{q}%"))

        if doc_kind:
            statement = statement.where(Document.metadata_["doc_kind"].astext == doc_kind)

        if language:
            statement = statement.where(Document.metadata_["language"].astext == language)

        if bank:
            statement = statement.where(Document.metadata_["bank"].contains([bank]))

        if charge_type:
            statement = statement.where(Document.metadata_["charge_type"].contains([charge_type]))

        statement = statement.order_by(Document.id).offset(offset).limit(limit)

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get(self, document_id: int) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()
