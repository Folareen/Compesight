import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompetitorStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    muted = "muted"


class Competitor(Base):
    __tablename__ = "competitor"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String)
    website_url: Mapped[str] = mapped_column(String)
    status: Mapped[CompetitorStatus] = mapped_column(
        Enum(CompetitorStatus, name="competitor_status"), default=CompetitorStatus.pending
    )
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
