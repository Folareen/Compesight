import uuid
from datetime import datetime

from pydantic import BaseModel


class SnapshotOut(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    fetched_at: datetime
    content_hash: str
    raw_payload: str | None
    http_status: int | None
    error: str | None
