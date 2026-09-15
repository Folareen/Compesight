import uuid

from pydantic import BaseModel

from app.models.finding import ChangeType, Urgency


class RoutingRuleIn(BaseModel):
    competitor_id: uuid.UUID | None
    change_type: ChangeType | None
    min_urgency: Urgency
    channels: list[uuid.UUID]
    enabled: bool


class RoutingRuleOut(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID | None
    change_type: ChangeType | None
    min_urgency: Urgency
    channels: list[uuid.UUID]
    enabled: bool


class RoutingRuleListIn(BaseModel):
    rules: list[RoutingRuleIn]


class RoutingRuleListOut(BaseModel):
    rules: list[RoutingRuleOut]
