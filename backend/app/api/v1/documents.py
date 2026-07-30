from typing import List, Optional
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.documents import DocumentResponse, DocumentStatusResponse
from app.services.pdf_service import pdf_service
from app.services.rag_service import rag_service
from app.services.storage_service import storage_service
from app.api.deps import verify_workspace_access, require_workspace_role

logger = structlog.get_logger()
router = APIRouter()


async def process_document_background(
    document_id: str,
    file_bytes: bytes,
    original_filename: str,
    owner_id: str,
    workspace_id: Optional[str],
):
    """Background task: upload, extract, chunk, embed. Never crashes the main request."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            # Storage (S3 or local, never crashes)
            try:
                storage_result = await storage_service.upload_pdf(file_bytes, original_filename, owner_id)
                doc.s3_key = storage_result.get("s3_key")
                doc.s3_url = storage_result.get("s3_url")
                doc.local_path = storage_result.get("local_path")
            except Exception as e:
                logger.warning("Storage failed, continuing", error=str(e))

            # Extract text
            full_text, page_count, _ = await pdf_service.extract_text(file_bytes)
            page_map = pdf_service.build_chunk_page_map(full_text, settings.CHUNK_SIZE)
            doc.page_count = page_count

            if not full_text.strip():
                doc.status = DocumentStatus.FAILED
                doc.error_message = "No extractable text found in PDF (may be scanned/image-only)"
                await db.commit()
                return

            # Embed and store
            chunk_count = await rag_service.ingest_document(
                document_id=document_id,
                text_content=full_text,
                document_title=doc.title,
                owner_id=owner_id,
                workspace_id=workspace_id,
                page_map=page_map,
            )

            doc.chunk_count = chunk_count
            doc.status = DocumentStatus.READY
            await db.commit()
            logger.info("Document processing complete", document_id=document_id, chunks=chunk_count)

        except Exception as e:
            logger.error("Document processing failed", document_id=document_id, error=str(e))
            try:
                result = await db.execute(select(Document).where(Document.id == document_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)[:500]
                    await db.commit()
            except Exception:
                pass


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    workspace_id: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # NEW: verify membership BEFORE doing any file work. Fails fast, and
    # closes the IDOR bug where any workspace_id was accepted unchecked.
    if workspace_id:
        await verify_workspace_access(workspace_id, current_user, db)

    file_bytes = await file.read()
    file_size = len(file_bytes)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    doc_title = title or file.filename.replace(".pdf", "").replace("_", " ").title()
    document = Document(
        title=doc_title,
        filename=file.filename,
        file_size=file_size,
        owner_id=current_user.id,
        workspace_id=workspace_id,
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    await db.flush()

    background_tasks.add_task(
        process_document_background,
        document.id, file_bytes, file.filename, current_user.id, workspace_id,
    )

    return document


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if workspace_id:
        # NEW: must be a verified member to list a workspace's documents —
        # and once verified, see ALL of that workspace's documents, not
        # just your own. This is the sharing behavior that was missing.
        await verify_workspace_access(workspace_id, current_user, db)
        query = select(Document).where(Document.workspace_id == workspace_id)
    else:
        # No workspace given = your personal (non-workspace) documents only.
        query = select(Document).where(
            Document.owner_id == current_user.id,
            Document.workspace_id.is_(None),
        )

    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def _get_accessible_document(document_id: str, current_user: User, db: AsyncSession) -> Document:
    """
    Shared lookup for get_document / get_document_status / delete_document.
    Accessible if you own it, or you're a verified member of its workspace.
    Returns 404 (not 403) on failure so we don't leak document existence
    to users who can't see it.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.owner_id == current_user.id:
        return doc

    if doc.workspace_id:
        member_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == doc.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
        )
        if member_result.scalar_one_or_none():
            return doc

    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_accessible_document(document_id, current_user, db)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_accessible_document(document_id, current_user, db)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await _get_accessible_document(document_id, current_user, db)

    # NEW: uploader can always delete their own doc. Anyone else must be a
    # workspace OWNER/ADMIN — a plain MEMBER/VIEWER who can now SEE a shared
    # document (per the fix above) still shouldn't be able to delete it.
    if doc.owner_id != current_user.id:
        member_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == doc.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
        )
        membership = member_result.scalar_one_or_none()
        require_workspace_role(membership, WorkspaceRole.OWNER, WorkspaceRole.ADMIN)

    # Best-effort cleanup — never let cleanup failures block deletion (unchanged)
    try:
        await rag_service.delete_document_vectors(document_id)
    except Exception as e:
        logger.warning("Vector cleanup failed", error=str(e))

    try:
        await storage_service.delete_file(s3_key=doc.s3_key, local_path=doc.local_path)
    except Exception as e:
        logger.warning("Storage cleanup failed", error=str(e))

    await db.delete(doc)
