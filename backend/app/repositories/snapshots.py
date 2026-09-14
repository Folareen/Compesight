import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import Snapshot
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    source_id: uuid.UUID,
    fetched_at: datetime,
    content_hash: str,
    raw_payload: str | None,
    http_status: int | None,
    error: str | None,
) -> Snapshot:
    snapshot = Snapshot(
        workspace_id=workspace_id,
        source_id=source_id,
        fetched_at=fetched_at,
        content_hash=content_hash,
        raw_payload=raw_payload,
        http_status=http_status,
        error=error,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def get(db: AsyncSession, workspace_id: uuid.UUID, snapshot_id: uuid.UUID) -> Snapshot | None:
    return await get_scoped_or_404(db, Snapshot, workspace_id, snapshot_id)


async def get_latest_successful(
    db: AsyncSession, workspace_id: uuid.UUID, source_id: uuid.UUID
) -> Snapshot | None:
    stmt = workspace_scoped(
        select(Snapshot)
        .where(Snapshot.source_id == source_id, Snapshot.error.is_(None))
        .order_by(Snapshot.fetched_at.desc())
        .limit(1),
        Snapshot,
        workspace_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest(db: AsyncSession, workspace_id: uuid.UUID, source_id: uuid.UUID) -> Snapshot | None:
    """Most recent snapshot regardless of success — used for the
    content-hash short-circuit, which must compare against the last
    *attempt*, not the last success (a failed crawl has no content to
    compare, but its predecessor's hash is still the right baseline)."""
    stmt = workspace_scoped(
        select(Snapshot).where(Snapshot.source_id == source_id).order_by(Snapshot.fetched_at.desc()).limit(1),
        Snapshot,
        workspace_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
