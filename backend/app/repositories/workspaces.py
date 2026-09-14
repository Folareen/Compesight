import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole


async def create_with_owner(db: AsyncSession, name: str, slug: str, user_id: uuid.UUID) -> Workspace:
    workspace = Workspace(name=name, slug=slug)
    db.add(workspace)
    await db.flush()

    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user_id, role=WorkspaceRole.owner))
    await db.flush()
    return workspace


async def get_by_id(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    return result.scalar_one_or_none()


async def get_first_membership_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> WorkspaceMember | None:
    """The workspace a user lands in by default.

    Phase 0 gives every new user exactly one workspace, so "first" is
    unambiguous. Workspace switching for users with multiple memberships
    is out of scope until the spec calls for it.
    """
    result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
    )
    return result.scalars().first()
