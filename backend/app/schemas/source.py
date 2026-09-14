import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.source import SourceStatus, SourceType
from app.schemas.extraction_fields import SourceConfig


class SourceOut(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    type: SourceType
    url: str
    crawl_interval_seconds: int
    status: SourceStatus
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int
    blocked_reason: str | None


class SourceCreateIn(BaseModel):
    type: SourceType
    url: str
    crawl_interval_seconds: int
    config: SourceConfig = SourceConfig()


class SourceHealthOut(BaseModel):
    status: SourceStatus
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int
    blocked_reason: str | None
