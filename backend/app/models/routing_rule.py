import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.finding import ChangeType, Urgency


class RoutingRule(Base):
    __tablename__ = "routing_rule"
    __table_args__ = (
        Index("ix_routing_rule_workspace_competitor", "workspace_id", "competitor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    # Null = workspace default, applies to every competitor.
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitor.id", ondelete="CASCADE"), nullable=True
    )
    # Null = every change type.
    change_type: Mapped[ChangeType | None] = mapped_column(
        Enum(ChangeType, name="change_type"), nullable=True
    )
    min_urgency: Mapped[Urgency] = mapped_column(Enum(Urgency, name="urgency"))
    channels: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
