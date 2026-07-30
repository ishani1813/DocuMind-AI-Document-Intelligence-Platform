from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.document import Document
from app.schemas.documents import CreateWorkspaceRequest, WorkspaceResponse, InviteMemberRequest

router = APIRouter()


@router.post("/", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = Workspace(name=payload.name, description=payload.description, owner_id=current_user.id)
    db.add(workspace)
    await db.flush()

    member = WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role=WorkspaceRole.OWNER)
    db.add(member)
    await db.flush()

    return WorkspaceResponse(
        id=workspace.id, name=workspace.name, description=workspace.description,
        owner_id=workspace.owner_id, member_count=1, document_count=0, created_at=workspace.created_at,
    )


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Workspace).join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    workspaces = result.scalars().all()

    output = []
    for ws in workspaces:
        members = await db.execute(select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id))
        docs = await db.execute(select(Document).where(Document.workspace_id == ws.id))
        output.append(WorkspaceResponse(
            id=ws.id, name=ws.name, description=ws.description, owner_id=ws.owner_id,
            member_count=len(members.scalars().all()), document_count=len(docs.scalars().all()),
            created_at=ws.created_at,
        ))
    return output


@router.post("/{workspace_id}/invite")
async def invite_member(
    workspace_id: str,
    payload: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.role.in_([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only owners/admins can invite members")

    user_result = await db.execute(select(User).where(User.email == payload.email))
    invited_user = user_result.scalar_one_or_none()
    if not invited_user:
        raise HTTPException(status_code=404, detail="User with that email not found")

    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == invited_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    role = WorkspaceRole(payload.role) if payload.role in WorkspaceRole.__members__.values() else WorkspaceRole.MEMBER
    member = WorkspaceMember(workspace_id=workspace_id, user_id=invited_user.id, role=role)
    db.add(member)
    return {"message": f"{invited_user.full_name} added to workspace"}


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await db.delete(ws)
