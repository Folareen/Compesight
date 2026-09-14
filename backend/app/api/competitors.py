import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.competitor import Competitor
from app.models.source import Source
from app.repositories import competitors as competitors_repo
from app.repositories import sources as sources_repo
from app.schemas.competitor import CompetitorCreateIn, CompetitorOut, CompetitorUpdateIn
from app.schemas.source import SourceCreateIn, SourceOut

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("", response_model=list[CompetitorOut])
async def list_competitors(
    ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)
) -> list[Competitor]:
    return await competitors_repo.list_for_workspace(db, ctx.workspace_id)


@router.post("", response_model=CompetitorOut, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    body: CompetitorCreateIn,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Competitor:
    competitor = await competitors_repo.create(db, ctx.workspace_id, body.name, body.website_url)
    await db.commit()
    return competitor


@router.get("/{competitor_id}", response_model=CompetitorOut)
async def get_competitor(
    competitor_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Competitor:
    competitor = await competitors_repo.get(db, ctx.workspace_id, competitor_id)
    if competitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")
    return competitor


@router.patch("/{competitor_id}", response_model=CompetitorOut)
async def update_competitor(
    competitor_id: uuid.UUID,
    body: CompetitorUpdateIn,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Competitor:
    competitor = await competitors_repo.update(
        db, ctx.workspace_id, competitor_id, name=body.name, status=body.status
    )
    if competitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")
    await db.commit()
    return competitor


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await competitors_repo.delete(db, ctx.workspace_id, competitor_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")
    await db.commit()


@router.get("/{competitor_id}/sources", response_model=list[SourceOut])
async def list_sources(
    competitor_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> list[Source]:
    competitor = await competitors_repo.get(db, ctx.workspace_id, competitor_id)
    if competitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")
    return await sources_repo.list_for_competitor(db, ctx.workspace_id, competitor.id)


@router.post("/{competitor_id}/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(
    competitor_id: uuid.UUID,
    body: SourceCreateIn,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Source:
    competitor = await competitors_repo.get(db, ctx.workspace_id, competitor_id)
    if competitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")

    source = await sources_repo.create(
        db,
        ctx.workspace_id,
        competitor.id,
        body.type,
        body.url,
        body.config.model_dump(mode="json"),
        body.crawl_interval_seconds,
    )
    await db.commit()
    return source
