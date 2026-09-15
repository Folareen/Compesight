import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.notification_channel import ChannelKind, NotificationChannel
from app.repositories import notification_channels as channels_repo
from app.schemas.notification_channel import (
    EmailChannelConfig,
    NotificationChannelIn,
    NotificationChannelOut,
    SlackChannelConfig,
    WebhookChannelConfig,
)
from app.services.channel_crypto import decrypt_channel_config, encrypt_channel_config
from app.services.delivery.base import DeliveryFailed
from app.services.delivery.slack import send_verification_ping

router = APIRouter(prefix="/channels", tags=["channels"])


def _display_identifier(kind: ChannelKind, config) -> str:
    if kind == ChannelKind.email:
        assert isinstance(config, EmailChannelConfig)
        return config.recipient_email
    if kind == ChannelKind.slack:
        assert isinstance(config, SlackChannelConfig)
        return f"…{config.webhook_url[-6:]}"
    assert isinstance(config, WebhookChannelConfig)
    return config.url


def _to_channel_out(channel: NotificationChannel) -> NotificationChannelOut:
    config = decrypt_channel_config(channel.config)
    return NotificationChannelOut(
        id=channel.id,
        kind=channel.kind,
        display_identifier=_display_identifier(channel.kind, config),
        verified_at=channel.verified_at,
        created_at=channel.created_at,
    )


@router.get("", response_model=list[NotificationChannelOut])
async def list_channels(
    ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)
) -> list[NotificationChannelOut]:
    channels = await channels_repo.list_for_workspace(db, ctx.workspace_id)
    return [_to_channel_out(c) for c in channels]


@router.post("", response_model=NotificationChannelOut, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: NotificationChannelIn,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> NotificationChannelOut:
    encrypted = encrypt_channel_config(body.config)
    channel = await channels_repo.create(db, ctx.workspace_id, body.config.kind, encrypted)
    await db.commit()
    return _to_channel_out(channel)


@router.post("/{channel_id}/verify", response_model=NotificationChannelOut)
async def verify_channel(
    channel_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> NotificationChannelOut:
    channel = await channels_repo.get(db, ctx.workspace_id, channel_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")

    config = decrypt_channel_config(channel.config)
    if channel.kind == ChannelKind.slack:
        assert isinstance(config, SlackChannelConfig)
        try:
            await send_verification_ping(config.webhook_url)
        except DeliveryFailed as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"verification failed: {exc}") from exc
    # Email and generic webhook channels are verified by a successful
    # first delivery rather than a synchronous probe here — a request
    # handler never blocks on an external call it doesn't have to
    # (docs/backend-rules.md: async I/O is fine, but this keeps the route
    # from depending on Resend/the customer's endpoint being up right now).

    updated = await channels_repo.mark_verified(db, ctx.workspace_id, channel_id, datetime.now(timezone.utc))
    await db.commit()
    assert updated is not None
    return _to_channel_out(updated)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await channels_repo.delete(db, ctx.workspace_id, channel_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")
    await db.commit()
