import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.competitor import CompetitorStatus


class CompetitorOut(BaseModel):
    id: uuid.UUID
    name: str
    website_url: str
    status: CompetitorStatus
    muted_until: datetime | None
    created_at: datetime


class CompetitorCreateIn(BaseModel):
    name: str
    website_url: str


class CompetitorUpdateIn(BaseModel):
    name: str | None = None
    status: CompetitorStatus | None = None
