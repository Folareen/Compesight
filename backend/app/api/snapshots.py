import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.repositories import snapshots as snapshots_repo
from app.schemas.snapshot import SnapshotOut

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.get("/{snapshot_id}", response_model=SnapshotOut)
async def get_snapshot(
    snapshot_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    snapshot = await snapshots_repo.get(db, ctx.workspace_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "snapshot not found")
    return snapshot
