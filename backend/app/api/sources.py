import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.source import SourceStatus
from app.repositories import sources as sources_repo
from app.schemas.source import SourceHealthOut
from app.tasks.crawling import crawl_source_task

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/{source_id}/health", response_model=SourceHealthOut)
async def get_source_health(
    source_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    source = await sources_repo.get(db, ctx.workspace_id, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    return source


@router.post("/{source_id}/crawl", status_code=status.HTTP_202_ACCEPTED)
async def trigger_crawl(
    source_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    source = await sources_repo.get(db, ctx.workspace_id, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    if source.status == SourceStatus.blocked:
        raise HTTPException(status.HTTP_409_CONFLICT, "source is blocked and cannot be crawled")

    task = crawl_source_task.delay(str(source.id))
    return {"task_id": task.id}
