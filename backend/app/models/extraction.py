import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractionMethod(str, enum.Enum):
    selector = "selector"
    llm = "llm"
    mixed = "mixed"


class Extraction(Base):
    __tablename__ = "extraction"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshot.id", ondelete="CASCADE"), unique=True
    )
    schema_version: Mapped[int] = mapped_column(Integer)
    fields: Mapped[dict] = mapped_column(JSONB)
    method: Mapped[ExtractionMethod] = mapped_column(Enum(ExtractionMethod, name="extraction_method"))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
