import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.finding import ChangeType, ClassificationStatus, Urgency


class FieldChangeOut(BaseModel):
    path: str
    old_value: str | int | bool | list[str] | None
    new_value: str | int | bool | list[str] | None


class FindingOut(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    source_id: uuid.UUID
    snapshot_id: uuid.UUID
    change_type: ChangeType
    urgency: Urgency
    title: str
    summary: str
    changeset: list[FieldChangeOut]
    is_baseline: bool
    classification_status: ClassificationStatus
    detected_at: datetime


class FindingListOut(BaseModel):
    data: list[FindingOut]
    next_cursor: str | None
    has_more: bool
