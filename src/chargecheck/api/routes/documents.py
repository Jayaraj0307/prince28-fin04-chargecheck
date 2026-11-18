from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from chargecheck.db.models import Document
from chargecheck.db.session import SessionLocal

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
async def list_documents():
    async with SessionLocal() as session:
        result = await session.execute(select(Document))
        documents = result.scalars().all()

        return [
            {
                "id": doc.id,
                "external_id": doc.external_id,
                "title": doc.title,
                "doc_type": doc.doc_type,
            }
            for doc in documents
        ]


@router.get("/{document_id}")
async def get_document(document_id: int):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()

        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "id": doc.id,
            "external_id": doc.external_id,
            "title": doc.title,
            "doc_type": doc.doc_type,
        }
