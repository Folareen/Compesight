import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorStatus
from app.models.source import Source, SourceStatus, SourceType
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor_id: uuid.UUID,
    type: SourceType,
    url: str,
    config: dict,
    crawl_interval_seconds: int,
) -> Source:
    source = Source(
        workspace_id=workspace_id,
        competitor_id=competitor_id,
        type=type,
        url=url,
        config=config,
        crawl_interval_seconds=crawl_interval_seconds,
    )
    db.add(source)
    await db.flush()
    return source


async def list_for_competitor(
    db: AsyncSession, workspace_id: uuid.UUID, competitor_id: uuid.UUID
) -> list[Source]:
    stmt = workspace_scoped(
        select(Source).where(Source.competitor_id == competitor_id), Source, workspace_id
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get(db: AsyncSession, workspace_id: uuid.UUID, source_id: uuid.UUID) -> Source | None:
    return await get_scoped_or_404(db, Source, workspace_id, source_id)


async def update_health(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    status: SourceStatus,
    last_attempt_at: datetime,
    last_success_at: datetime | None,
    consecutive_failures: int,
    blocked_reason: str | None,
) -> Source | None:
    source = await get_scoped_or_404(db, Source, workspace_id, source_id)
    if source is None:
        return None
    source.status = status
    source.last_attempt_at = last_attempt_at
    if last_success_at is not None:
        source.last_success_at = last_success_at
    source.consecutive_failures = consecutive_failures
    source.blocked_reason = blocked_reason
    await db.flush()
    return source


async def get_due_for_crawl(db: AsyncSession, now: datetime, limit: int) -> list[Source]:
    """Sources due for a scheduled crawl, across every workspace.

    Not workspace-scoped by design: the scheduler is a system job, not a
    session-derived request — see docs/rules.md rule 1's framing of
    workspace scoping as "derived from the authenticated session, always".
    There is no session here, and this function returns only ids used to
    enqueue crawl tasks, never data rendered to a user. Every downstream
    read (crawl results, findings, health) re-scopes on workspace_id as
    usual, so isolation is never actually weakened by this query existing.

    Due = never attempted, or now >= last_attempt_at + interval. Excludes
    `blocked` sources (terminal until a human clears them) and competitors
    that are `muted`. Does NOT exclude `pending` competitors — a source on
    a newly added competitor should still be crawled on schedule.
    """
    due_at = Source.last_attempt_at + func.make_interval(0, 0, 0, 0, 0, 0, Source.crawl_interval_seconds)
    stmt = (
        select(Source)
        .join(Competitor, Source.competitor_id == Competitor.id)
        .where(
            Source.status != SourceStatus.blocked,
            Competitor.status != CompetitorStatus.muted,
            or_(Source.last_attempt_at.is_(None), due_at <= now),
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
