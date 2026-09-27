from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_case_for_user, get_current_user
from models.user import User
from schemas.search import SearchHit, SearchRequest, SearchResponse
from services.rag_service import Corpus, RAGService

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SearchResponse:
    case_id: str | None = None
    if body.corpus is Corpus.CASE:
        if body.case_id is None:
            raise HTTPException(status_code=400, detail="case_id is required for the CASE corpus")
        case = await get_case_for_user(str(body.case_id), user, db)  # enforces org ownership
        case_id = str(case.id)
    rag = RAGService(db)
    chunks = await rag.retrieve(
        body.query,
        body.corpus,
        case_id=case_id,
        institution=body.institution,
        top_k=body.top_k,
        mode=body.mode,
        org_id=str(user.org_id) if case_id else None,
    )
    return SearchResponse(
        query=body.query,
        corpus=body.corpus,
        mode=body.mode,
        results=[SearchHit(**c.to_dict()) for c in chunks],
        source_not_found=not chunks,
    )
