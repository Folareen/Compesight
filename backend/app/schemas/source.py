import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field

from app.config import settings
from app.models.source import SourceStatus, SourceType
from app.schemas.extraction_fields import SourceConfig


class _ExtractionDriftMixin(BaseModel):
    extraction_failure_streak: int

    @computed_field
    @property
    def extraction_drift(self) -> bool:
        """True once repeated extraction misses look like the page changed
        shape rather than a one-off parsing fluke — the threshold lives in
        one place (settings) instead of being duplicated in the frontend."""
        return self.extraction_failure_streak >= settings.extraction_drift_threshold


class SourceOut(_ExtractionDriftMixin):
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


class SourceHealthOut(_ExtractionDriftMixin):
    status: SourceStatus
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int
    blocked_reason: str | None
