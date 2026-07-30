from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.documents import SearchRequest, SearchResponse, SearchResult
from app.services.rag_service import rag_service

router = APIRouter()


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(payload: SearchRequest, current_user: User = Depends(get_current_user)):
    results = await rag_service.semantic_search(
        query=payload.query, owner_id=current_user.id,
        document_ids=payload.document_ids, workspace_id=payload.workspace_id,
        top_k=payload.top_k,
    )
    return SearchResponse(
        query=payload.query,
        results=[SearchResult(**r) for r in results],
        total=len(results),
    )
