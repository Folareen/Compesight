import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_channel import ChannelKind, NotificationChannel
from app.repositories.scoped import get_scoped_or_404, workspace_scoped


async def create(
    db: AsyncSession, workspace_id: uuid.UUID, kind: ChannelKind, encrypted_config: dict
) -> NotificationChannel:
    channel = NotificationChannel(workspace_id=workspace_id, kind=kind, config=encrypted_config)
    db.add(channel)
    await db.flush()
    return channel


async def get(db: AsyncSession, workspace_id: uuid.UUID, channel_id: uuid.UUID) -> NotificationChannel | None:
    return await get_scoped_or_404(db, NotificationChannel, workspace_id, channel_id)


async def get_many(
    db: AsyncSession, workspace_id: uuid.UUID, channel_ids: list[uuid.UUID]
) -> list[NotificationChannel]:
    stmt = workspace_scoped(
        select(NotificationChannel).where(NotificationChannel.id.in_(channel_ids)),
        NotificationChannel,
        workspace_id,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> list[NotificationChannel]:
    stmt = workspace_scoped(select(NotificationChannel), NotificationChannel, workspace_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_verified(
    db: AsyncSession, workspace_id: uuid.UUID, channel_id: uuid.UUID, verified_at: datetime
) -> NotificationChannel | None:
    channel = await get_scoped_or_404(db, NotificationChannel, workspace_id, channel_id)
    if channel is None:
        return None
    channel.verified_at = verified_at
    await db.flush()
    return channel


async def delete(db: AsyncSession, workspace_id: uuid.UUID, channel_id: uuid.UUID) -> bool:
    channel = await get_scoped_or_404(db, NotificationChannel, workspace_id, channel_id)
    if channel is None:
        return False
    await db.delete(channel)
    await db.flush()
    return True
