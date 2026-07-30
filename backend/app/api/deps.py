"""
Shared dependencies for workspace-scoped resource access.

Save this as: backend/app/api/deps.py

This is the piece that was missing: workspace_id was accepted from the
client and stored on Document, but nothing ever checked that the current
user was actually a member of that workspace before reading/writing to it.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole


async def verify_workspace_access(
    workspace_id: str,
    current_user: User,
    db: AsyncSession,
) -> WorkspaceMember:
    """
    Confirm current_user is a member of workspace_id.

    Raises 403 if they are not a member (previously: no check existed at all,
    so any authenticated user could pass any workspace_id on upload/list and
    it would be silently accepted).

    Returns the WorkspaceMember row so callers can also check `.role`.
    """
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )
    return membership


def require_workspace_role(membership: WorkspaceMember, *allowed: WorkspaceRole) -> None:
    """
    Raise 403 unless membership.role is one of `allowed`.

    Usage: require_workspace_role(membership, WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
    """
    if membership.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of: {[r.value for r in allowed]}",
        )
