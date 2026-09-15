import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


async def create_if_absent(
    db: AsyncSession, workspace_id: uuid.UUID, finding_id: uuid.UUID, channel_id: uuid.UUID
) -> Alert | None:
    """Insert a pending alert for this finding+channel pair, or return None
    if one already exists. `ON CONFLICT DO NOTHING` on the unique
    constraint makes a retried routing pass idempotent without a
    read-then-write race (docs/rules.md: jobs run at least twice)."""
    stmt = (
        pg_insert(Alert)
        .values(workspace_id=workspace_id, finding_id=finding_id, channel_id=channel_id)
        .on_conflict_do_nothing(constraint="uq_alert_finding_channel")
        .returning(Alert)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.scalar_one_or_none()


async def get(db: AsyncSession, workspace_id: uuid.UUID, alert_id: uuid.UUID) -> Alert | None:
    return await get_scoped_or_404(db, Alert, workspace_id, alert_id)


async def mark_sent(db: AsyncSession, alert: Alert, sent_at: datetime) -> None:
    alert.status = AlertStatus.sent
    alert.sent_at = sent_at
    await db.flush()


async def record_failed_attempt(db: AsyncSession, alert: Alert, error: str, *, final: bool) -> None:
    alert.attempts += 1
    alert.last_error = error
    if final:
        alert.status = AlertStatus.failed
    await db.flush()


async def list_for_finding(db: AsyncSession, workspace_id: uuid.UUID, finding_id: uuid.UUID) -> list[Alert]:
    stmt = workspace_scoped(select(Alert).where(Alert.finding_id == finding_id), Alert, workspace_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
