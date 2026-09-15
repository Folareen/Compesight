from pydantic import BaseModel, ConfigDict

from app.models.finding import ChangeType, Urgency


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_type: ChangeType
    urgency: Urgency
    title: str
    summary: str
