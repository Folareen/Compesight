import base64
import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ChangeType, ClassificationStatus, Finding, Urgency
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


def encode_cursor(detected_at: datetime, finding_id: uuid.UUID) -> str:
    raw = f"{detected_at.isoformat()}|{finding_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    detected_at_str, id_str = raw.split("|")
    return datetime.fromisoformat(detected_at_str), uuid.UUID(id_str)


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor_id: uuid.UUID,
    source_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    change_type: ChangeType,
    urgency: Urgency,
    title: str,
    summary: str,
    changeset: dict,
    is_baseline: bool,
    dedupe_key: str,
    classification_status: ClassificationStatus,
) -> Finding:
    finding = Finding(
        workspace_id=workspace_id,
        competitor_id=competitor_id,
        source_id=source_id,
        snapshot_id=snapshot_id,
        change_type=change_type,
        urgency=urgency,
        title=title,
        summary=summary,
        changeset=changeset,
        is_baseline=is_baseline,
        dedupe_key=dedupe_key,
        classification_status=classification_status,
    )
    db.add(finding)
    await db.flush()
    return finding


async def get(db: AsyncSession, workspace_id: uuid.UUID, finding_id: uuid.UUID) -> Finding | None:
    return await get_scoped_or_404(db, Finding, workspace_id, finding_id)


async def get_by_dedupe_key(db: AsyncSession, workspace_id: uuid.UUID, dedupe_key: str) -> Finding | None:
    stmt = workspace_scoped(
        select(Finding).where(Finding.dedupe_key == dedupe_key), Finding, workspace_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_for_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    competitor_id: uuid.UUID | None = None,
    change_type: ChangeType | None = None,
    urgency: Urgency | None = None,
    since: datetime | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[Finding], str | None]:
    stmt = workspace_scoped(select(Finding), Finding, workspace_id)

    if competitor_id is not None:
        stmt = stmt.where(Finding.competitor_id == competitor_id)
    if change_type is not None:
        stmt = stmt.where(Finding.change_type == change_type)
    if urgency is not None:
        stmt = stmt.where(Finding.urgency == urgency)
    if since is not None:
        stmt = stmt.where(Finding.detected_at >= since)
    if cursor is not None:
        cursor_detected_at, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Finding.detected_at < cursor_detected_at,
                and_(Finding.detected_at == cursor_detected_at, Finding.id < cursor_id),
            )
        )

    stmt = stmt.order_by(Finding.detected_at.desc(), Finding.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].detected_at, page[-1].id) if has_more and page else None
    return page, next_cursor
