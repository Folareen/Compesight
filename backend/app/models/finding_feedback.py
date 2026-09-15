import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.finding import ChangeType, Urgency


class FeedbackVerdict(str, enum.Enum):
    useful = "useful"
    noise = "noise"


class FindingFeedback(Base):
    __tablename__ = "finding_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finding.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"))
    verdict: Mapped[FeedbackVerdict] = mapped_column(Enum(FeedbackVerdict, name="feedback_verdict"))
    corrected_change_type: Mapped[ChangeType | None] = mapped_column(
        Enum(ChangeType, name="change_type"), nullable=True
    )
    corrected_urgency: Mapped[Urgency | None] = mapped_column(Enum(Urgency, name="urgency"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
