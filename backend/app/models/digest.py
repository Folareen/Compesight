import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Digest(Base):
    __tablename__ = "digest"
    __table_args__ = (
        # A redelivered or manually retried send_digest_task must not
        # create a second row for the same period (docs/rules.md: jobs
        # run at least twice) — same idempotency shape as
        # uq_alert_finding_channel on the `alert` table.
        UniqueConstraint("workspace_id", "period_start", "period_end", name="uq_digest_workspace_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finding_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
