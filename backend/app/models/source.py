import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceType(str, enum.Enum):
    website = "website"
    pricing_page = "pricing_page"
    rss = "rss"
    reddit = "reddit"
    hackernews = "hackernews"
    producthunt = "producthunt"
    youtube = "youtube"
    github = "github"
    appstore = "appstore"
    playstore = "playstore"


class SourceStatus(str, enum.Enum):
    healthy = "healthy"
    degraded = "degraded"
    failing = "failing"
    blocked = "blocked"


class Source(Base):
    __tablename__ = "source"
    __table_args__ = (Index("ix_source_status_last_attempt_at", "status", "last_attempt_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitor.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"))
    url: Mapped[str] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    crawl_interval_seconds: Mapped[int] = mapped_column(Integer)

    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status"), default=SourceStatus.healthy
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    blocked_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_failure_streak: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
