from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ── Documents ─────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_size: int
    page_count: int
    status: str
    chunk_count: int
    s3_url: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    id: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None


# ── Chat ──────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    document_id: str
    document_title: str
    page_number: int
    chunk_text: str
    relevance_score: float


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[List[SourceCitation]] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    model_config = {"from_attributes": True}


class CreateSessionRequest(BaseModel):
    title: str = "New Conversation"
    workspace_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str
    document_ids: Optional[List[str]] = None


# ── Search ────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    document_ids: Optional[List[str]] = None
    top_k: int = 5
    workspace_id: Optional[str] = None


class SearchResult(BaseModel):
    document_id: str
    document_title: str
    page_number: int
    chunk_text: str
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int


# ── Workspaces ────────────────────────────────────────────────

class CreateWorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    member_count: int = 0
    document_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"
