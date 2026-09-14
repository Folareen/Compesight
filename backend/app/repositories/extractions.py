import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extraction import Extraction, ExtractionMethod
from app.models.snapshot import Snapshot
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    schema_version: int,
    fields: dict,
    method: ExtractionMethod,
    confidence: float | None,
) -> Extraction:
    extraction = Extraction(
        workspace_id=workspace_id,
        snapshot_id=snapshot_id,
        schema_version=schema_version,
        fields=fields,
        method=method,
        confidence=confidence,
    )
    db.add(extraction)
    await db.flush()
    return extraction


async def get_by_snapshot(
    db: AsyncSession, workspace_id: uuid.UUID, snapshot_id: uuid.UUID
) -> Extraction | None:
    stmt = workspace_scoped(
        select(Extraction).where(Extraction.snapshot_id == snapshot_id), Extraction, workspace_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get(db: AsyncSession, workspace_id: uuid.UUID, extraction_id: uuid.UUID) -> Extraction | None:
    return await get_scoped_or_404(db, Extraction, workspace_id, extraction_id)


async def get_latest_successful_for_source(
    db: AsyncSession, workspace_id: uuid.UUID, source_id: uuid.UUID, exclude_extraction_id: uuid.UUID | None = None
) -> Extraction | None:
    stmt = (
        select(Extraction)
        .join(Snapshot, Extraction.snapshot_id == Snapshot.id)
        .where(Snapshot.source_id == source_id, Snapshot.error.is_(None))
    )
    if exclude_extraction_id is not None:
        stmt = stmt.where(Extraction.id != exclude_extraction_id)
    stmt = workspace_scoped(
        stmt.order_by(Snapshot.fetched_at.desc()).limit(1), Extraction, workspace_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
