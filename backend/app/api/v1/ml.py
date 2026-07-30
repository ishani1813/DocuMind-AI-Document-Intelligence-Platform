"""ML API — classification, summarization, NER, sentiment, keywords, clustering, enhanced RAG."""

from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentStatus

logger = structlog.get_logger()
router = APIRouter()


class TextRequest(BaseModel):
    text: str


class SummarizeRequest(BaseModel):
    text: str
    mode: Literal["extractive", "abstractive"] = "extractive"
    max_sentences: int = 5
    max_tokens: int = 150


class ClassifyRequest(BaseModel):
    text: str
    custom_labels: Optional[List[str]] = None


class KeywordsRequest(BaseModel):
    text: str
    top_n: int = 20


class EnhancedChatRequest(BaseModel):
    query: str
    session_id: str
    document_ids: Optional[List[str]] = None
    use_hyde: bool = False
    use_rerank: bool = True
    top_k: int = 10


class ClusterRequest(BaseModel):
    workspace_id: Optional[str] = None
    n_clusters: Optional[int] = None


@router.post("/summarize")
async def summarize_text(payload: SummarizeRequest, current_user: User = Depends(get_current_user)):
    from app.ml.models.summarizer import document_summarizer
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: document_summarizer.summarize(payload.text, payload.mode, payload.max_sentences, payload.max_tokens))


@router.post("/classify")
async def classify_text(payload: ClassifyRequest, current_user: User = Depends(get_current_user)):
    from app.ml.models.classifier import document_classifier
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: document_classifier.classify(payload.text, payload.custom_labels))


@router.post("/keywords")
async def extract_keywords(payload: KeywordsRequest, current_user: User = Depends(get_current_user)):
    from app.ml.models.keywords import keyword_extractor
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: keyword_extractor.extract(payload.text, payload.top_n))


@router.post("/sentiment")
async def analyze_sentiment(payload: TextRequest, current_user: User = Depends(get_current_user)):
    from app.ml.models.sentiment import sentiment_analyzer
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: sentiment_analyzer.analyze(payload.text))


@router.post("/entities")
async def extract_entities(payload: TextRequest, current_user: User = Depends(get_current_user)):
    from app.ml.models.ner import ner_extractor
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: ner_extractor.extract(payload.text))


@router.post("/stats")
async def text_statistics(payload: TextRequest, current_user: User = Depends(get_current_user)):
    from app.ml.utils import text_preprocessor
    import asyncio
    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(None, text_preprocessor.compute_stats, payload.text)
    reading = await loop.run_in_executor(None, text_preprocessor.reading_level, payload.text)
    return {"stats": stats, "readability": reading}


@router.post("/chat/enhanced")
async def enhanced_chat(
    payload: EnhancedChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.ml.pipelines import rag_with_rerank
    from app.models.chat import ChatSession, ChatMessage

    result = await db.execute(select(ChatSession).where(ChatSession.id == payload.session_id, ChatSession.user_id == current_user.id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(select(ChatMessage).where(ChatMessage.session_id == payload.session_id).order_by(ChatMessage.created_at.asc()).limit(10))
    history = [{"role": m.role.value, "content": m.content} for m in msg_result.scalars().all()]

    return await rag_with_rerank.query(
        query=payload.query, owner_id=current_user.id, conversation_history=history,
        document_ids=payload.document_ids, use_hyde=payload.use_hyde,
        use_rerank=payload.use_rerank, top_k=payload.top_k,
    )


@router.post("/cluster")
async def cluster_documents(
    payload: ClusterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.ml.utils import document_clusterer

    query = select(Document).where(Document.owner_id == current_user.id, Document.status == DocumentStatus.READY)
    if payload.workspace_id:
        query = query.where(Document.workspace_id == payload.workspace_id)

    result = await db.execute(query)
    docs = result.scalars().all()

    if len(docs) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 ready documents to cluster")

    import asyncio
    doc_list = [{"id": d.id, "text": d.title, "title": d.title} for d in docs]
    loop = asyncio.get_event_loop()
    clusters = await loop.run_in_executor(None, lambda: document_clusterer.cluster(doc_list, payload.n_clusters))
    return {"document_count": len(docs), **clusters}
