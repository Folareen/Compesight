import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.competitor import Competitor
from app.models.source import Source, SourceType
from app.repositories import competitors as competitors_repo
from app.repositories import sources as sources_repo
from app.schemas.competitor import CompetitorCreateIn, CompetitorOut, CompetitorUpdateIn
from app.schemas.source import SourceCreateIn, SourceOut
from app.services.source_discovery import SourceSuggestion, discover_sources
from app.tasks.crawling import crawl_source_task

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


@router.get("/{competitor_id}/source-suggestions", response_model=list[SourceSuggestion])
async def get_source_suggestions(
    competitor_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> list[SourceSuggestion]:
    """Live probe, not a stored resource — nothing here is persisted until
    the user confirms a suggestion via the normal create_source endpoint."""
    competitor = await competitors_repo.get(db, ctx.workspace_id, competitor_id)
    if competitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")
    return await discover_sources(competitor.website_url)


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

    # Baseline crawl: don't make the user wait for the next scheduler tick
    # to see their first content (docs/build-plan.md Phase 2 done
    # condition — useful content within a minute of adding a competitor).
    # Only website/pricing_page go through Playwright today (docs/scraping.md);
    # other source types (RSS, GitHub, ...) land in Phase 6 with their own
    # fetch path and must wait for it rather than being run through this one.
    if source.type in (SourceType.website, SourceType.pricing_page):
        crawl_source_task.delay(str(source.id))

    return source
