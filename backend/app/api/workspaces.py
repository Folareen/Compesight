from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_workspace_context, WorkspaceContext
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories import workspaces as workspaces_repo
from app.schemas.workspace import WorkspaceBootstrapIn, WorkspaceOut
from app.services.workspace_onboarding import bootstrap_workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("/bootstrap", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def bootstrap(
    body: WorkspaceBootstrapIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    existing = await workspaces_repo.get_first_membership_for_user(db, user.id)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "user already has a workspace")

    workspace = await bootstrap_workspace(db, user_id=user.id, name=body.name)
    await db.commit()
    return workspace


@router.get("/current", response_model=WorkspaceOut)
async def current(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    workspace = await workspaces_repo.get_by_id(db, ctx.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "workspace not found")
    return workspace
