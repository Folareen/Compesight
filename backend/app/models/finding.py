import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChangeType(str, enum.Enum):
    pricing = "pricing"
    feature_launch = "feature_launch"
    messaging = "messaging"
    hiring = "hiring"
    funding = "funding"
    partnership = "partnership"
    content = "content"
    other = "other"


class Urgency(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ClassificationStatus(str, enum.Enum):
    ok = "ok"
    pending = "pending"
    failed = "failed"


class Finding(Base):
    __tablename__ = "finding"
    __table_args__ = (
        Index("ix_finding_workspace_dedupe_key", "workspace_id", "dedupe_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitor.id", ondelete="CASCADE")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE")
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshot.id", ondelete="CASCADE")
    )
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType, name="change_type"))
    urgency: Mapped[Urgency] = mapped_column(Enum(Urgency, name="urgency"))
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String)
    changeset: Mapped[dict] = mapped_column(JSONB)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str] = mapped_column(String)
    classification_status: Mapped[ClassificationStatus] = mapped_column(
        Enum(ClassificationStatus, name="classification_status"), default=ClassificationStatus.ok
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


Index(
    "ix_finding_workspace_competitor_detected_at",
    Finding.workspace_id,
    Finding.competitor_id,
    Finding.detected_at.desc(),
)
