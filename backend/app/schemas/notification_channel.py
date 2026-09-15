import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.notification_channel import ChannelKind


class EmailChannelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[ChannelKind.email] = ChannelKind.email
    recipient_email: str


class SlackChannelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[ChannelKind.slack] = ChannelKind.slack
    webhook_url: str


class WebhookChannelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[ChannelKind.webhook] = ChannelKind.webhook
    url: str
    secret: str | None = None


ChannelConfig = EmailChannelConfig | SlackChannelConfig | WebhookChannelConfig


class NotificationChannelIn(BaseModel):
    config: EmailChannelConfig | SlackChannelConfig | WebhookChannelConfig


class NotificationChannelOut(BaseModel):
    id: uuid.UUID
    kind: ChannelKind
    # The identifying part of the config only — never the raw secret/URL
    # back out over the API (docs/rules.md rule 2).
    display_identifier: str
    verified_at: datetime | None
    created_at: datetime
