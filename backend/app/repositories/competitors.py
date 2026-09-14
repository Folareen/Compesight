import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorStatus
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


async def create(db: AsyncSession, workspace_id: uuid.UUID, name: str, website_url: str) -> Competitor:
    competitor = Competitor(workspace_id=workspace_id, name=name, website_url=website_url)
    db.add(competitor)
    await db.flush()
    return competitor


async def list_for_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> list[Competitor]:
    stmt = workspace_scoped(select(Competitor), Competitor, workspace_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get(db: AsyncSession, workspace_id: uuid.UUID, competitor_id: uuid.UUID) -> Competitor | None:
    return await get_scoped_or_404(db, Competitor, workspace_id, competitor_id)


async def update(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor_id: uuid.UUID,
    *,
    name: str | None,
    status: CompetitorStatus | None,
) -> Competitor | None:
    """Apply a partial update. `None` for a field means "leave unchanged" —
    the route's request schema has no way to distinguish "unset" from
    "explicitly null" for these two fields since neither is nullable on the
    model, so this mirrors that directly rather than inventing a sentinel."""
    competitor = await get_scoped_or_404(db, Competitor, workspace_id, competitor_id)
    if competitor is None:
        return None
    if name is not None:
        competitor.name = name
    if status is not None:
        competitor.status = status
    await db.flush()
    return competitor


async def delete(db: AsyncSession, workspace_id: uuid.UUID, competitor_id: uuid.UUID) -> bool:
    competitor = await get_scoped_or_404(db, Competitor, workspace_id, competitor_id)
    if competitor is None:
        return False
    await db.delete(competitor)
    await db.flush()
    return True
