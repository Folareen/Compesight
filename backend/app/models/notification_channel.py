import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChannelKind(str, enum.Enum):
    email = "email"
    slack = "slack"
    webhook = "webhook"


class NotificationChannel(Base):
    __tablename__ = "notification_channel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[ChannelKind] = mapped_column(Enum(ChannelKind, name="channel_kind"))
    # Encrypted at rest (app.services.channel_crypto) — holds the Slack
    # webhook URL, recipient email, or generic webhook URL + secret.
    # Never logged (docs/rules.md rule 2).
    config: Mapped[dict] = mapped_column(JSONB)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
