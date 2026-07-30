from typing import List
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.schemas.documents import CreateSessionRequest, SendMessageRequest, ChatSessionResponse, ChatMessageResponse, SourceCitation
from app.services.rag_service import rag_service

logger = structlog.get_logger()
router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(title=payload.title, user_id=current_user.id, workspace_id=payload.workspace_id)
    db.add(session)
    await db.flush()
    return ChatSessionResponse(
        id=session.id, title=session.title,
        created_at=session.created_at, updated_at=session.updated_at, message_count=0,
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    output = []
    for s in sessions:
        count_result = await db.execute(select(ChatMessage).where(ChatMessage.session_id == s.id))
        count = len(count_result.scalars().all())
        output.append(ChatSessionResponse(
            id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at, message_count=count,
        ))
    return output


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ChatMessage(session_id=session_id, role=MessageRole.USER, content=payload.content)
    db.add(user_msg)
    await db.flush()

    history_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).limit(20)
    )
    history = [
        {"role": m.role.value, "content": m.content}
        for m in history_result.scalars().all() if m.id != user_msg.id
    ]

    logger.info("Running RAG chain", session_id=session_id, user=current_user.id)
    rag_result = await rag_service.chat_with_documents(
        query=payload.content, owner_id=current_user.id,
        conversation_history=history, document_ids=payload.document_ids,
        workspace_id=session.workspace_id, session_id=session_id,
    )

    if session.title == "New Conversation" and len(history) == 0:
        session.title = payload.content[:60] + ("..." if len(payload.content) > 60 else "")

    assistant_msg = ChatMessage(
        session_id=session_id, role=MessageRole.ASSISTANT,
        content=rag_result["answer"], sources=rag_result["sources"],
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatMessageResponse(
        id=assistant_msg.id, role=assistant_msg.role.value, content=assistant_msg.content,
        sources=[SourceCitation(**s) for s in (assistant_msg.sources or [])],
        created_at=assistant_msg.created_at,
    )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()
    return [
        ChatMessageResponse(
            id=m.id, role=m.role.value, content=m.content,
            sources=[SourceCitation(**s) for s in (m.sources or [])],
            created_at=m.created_at,
        )
        for m in messages
    ]
