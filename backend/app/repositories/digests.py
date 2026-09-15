import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digest import Digest
from app.repositories.scoped import workspace_scoped


async def get_latest(db: AsyncSession, workspace_id: uuid.UUID) -> Digest | None:
    stmt = workspace_scoped(
        select(Digest).order_by(Digest.period_end.desc()).limit(1), Digest, workspace_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_if_absent(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
    finding_ids: list[uuid.UUID],
) -> Digest | None:
    """Insert the digest for this period, or return None if one already
    exists for it. `ON CONFLICT DO NOTHING` on the unique constraint makes
    a redelivered or manually retried send_digest_task idempotent without
    a read-then-write race (docs/rules.md: jobs run at least twice)."""
    stmt = (
        pg_insert(Digest)
        .values(
            workspace_id=workspace_id,
            period_start=period_start,
            period_end=period_end,
            finding_ids=finding_ids,
        )
        .on_conflict_do_nothing(constraint="uq_digest_workspace_period")
        .returning(Digest)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.scalar_one_or_none()


async def mark_sent(db: AsyncSession, digest: Digest, sent_at: datetime) -> None:
    digest.sent_at = sent_at
    await db.flush()
