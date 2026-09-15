import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.finding import ChangeType, Urgency
from app.models.finding_feedback import FeedbackVerdict


class FindingFeedbackIn(BaseModel):
    verdict: FeedbackVerdict
    corrected_change_type: ChangeType | None = None
    corrected_urgency: Urgency | None = None


class FindingFeedbackOut(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    verdict: FeedbackVerdict
    corrected_change_type: ChangeType | None
    corrected_urgency: Urgency | None
    created_at: datetime
