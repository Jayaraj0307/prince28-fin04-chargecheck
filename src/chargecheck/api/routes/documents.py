from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from chargecheck.api.deps import StoreDep
from chargecheck.db.models import Document
from chargecheck.db.session import SessionLocal

router = APIRouter(prefix="/documents", tags=["documents"])

database_router = APIRouter(
    prefix="/database/documents",
    tags=["database-documents"],
)


# JSON-based document API
@router.get("")
def list_documents(
    store: StoreDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    rows = store.search(q)
    return {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": rows[offset : offset + limit],
    }


@router.get("/{doc_id}")
def get_document(doc_id: str, store: StoreDep) -> dict:
    record = store.get(doc_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document with id '{doc_id}'.",
        )
    return record


# PostgreSQL-based document API
@database_router.get("")
async def list_database_documents():
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured",
        )
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


@database_router.get("/{document_id}")
async def get_database_document(document_id: int):
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured",
        )
    async with SessionLocal() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()

        if doc is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        return {
            "id": doc.id,
            "external_id": doc.external_id,
            "title": doc.title,
            "doc_type": doc.doc_type,
        }
