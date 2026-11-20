"""PostgreSQL-backed document API."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from chargecheck.api.deps import RepoDep

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    repo: RepoDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    documents = await repo.list(q=q, limit=limit, offset=offset)

    return {
        "total": len(documents),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": doc.id,
                "external_id": doc.external_id,
                "title": doc.title,
                "doc_type": doc.doc_type,
            }
            for doc in documents
        ],
    }


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    repo: RepoDep,
) -> dict:
    document = await repo.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "id": document.id,
        "external_id": document.external_id,
        "title": document.title,
        "doc_type": document.doc_type,
    }
