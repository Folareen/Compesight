import asyncio
import random
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.config import settings
from app.db.session import async_session_factory
from app.models.alert import Alert
from app.models.competitor import Competitor
from app.models.finding import Finding
from app.models.notification_channel import ChannelKind, NotificationChannel
from app.repositories import alerts as alerts_repo
from app.schemas.notification_channel import EmailChannelConfig, SlackChannelConfig, WebhookChannelConfig
from app.services.channel_crypto import ChannelConfigDecryptionError, decrypt_channel_config
from app.services.delivery.base import AlertMessage, DeliveryFailed
from app.services.delivery.email import send_via_resend
from app.services.delivery.slack import send_via_slack_webhook
from app.services.delivery.webhook import send_via_generic_webhook


def _backoff_with_jitter(attempt: int) -> float:
    base = settings.alert_backoff_base_seconds * (2 ** (attempt - 1))
    capped = min(base, settings.alert_backoff_cap_seconds)
    return capped + random.uniform(0, settings.alert_backoff_jitter_seconds)


@celery_app.task(name="deliver_alert", bind=True, max_retries=settings.alert_delivery_max_retries)
def deliver_alert_task(self, alert_id: str) -> None:
    """Delivery retries independently of routing and classification
    (docs/architecture.md) — this task takes only the alert id, so a
    retry never re-derives the routing decision, only re-attempts the send."""
    retry_after = asyncio.run(_deliver_alert_async(uuid.UUID(alert_id), self.request.retries))
    if retry_after is not None:
        raise self.retry(countdown=retry_after)


async def _deliver_alert_async(alert_id: uuid.UUID, retries_so_far: int) -> float | None:
    async with async_session_factory() as db:
        alert = await db.get(Alert, alert_id)
        if alert is None:
            return None

        finding = await db.get(Finding, alert.finding_id)
        channel = await db.get(NotificationChannel, alert.channel_id)
        if finding is None or channel is None:
            return None

        competitor = await db.get(Competitor, finding.competitor_id)
        competitor_name = competitor.name if competitor is not None else "A competitor"

        message = AlertMessage.from_finding(
            finding,
            competitor_name,
            detail_url=f"{settings.dashboard_base_url}/competitors/{finding.competitor_id}/findings/{finding.id}",
        )

        try:
            await _send(channel, message)
        except ChannelConfigDecryptionError as exc:
            # Never recoverable by retrying — a bad or rotated encryption
            # key won't fix itself on the next attempt. Fail the alert
            # immediately rather than burning retries on it (docs/rules.md:
            # silence is never success — this still records last_error
            # instead of leaving the alert pending forever).
            await alerts_repo.record_failed_attempt(db, alert, str(exc), final=True)
            await db.commit()
            return None
        except DeliveryFailed as exc:
            is_final = retries_so_far >= settings.alert_delivery_max_retries
            await alerts_repo.record_failed_attempt(db, alert, str(exc), final=is_final)
            await db.commit()
            if is_final:
                return None
            return _backoff_with_jitter(retries_so_far + 1)

        await alerts_repo.mark_sent(db, alert, datetime.now(timezone.utc))
        await db.commit()
        return None


async def _send(channel: NotificationChannel, message: AlertMessage) -> None:
    config = decrypt_channel_config(channel.config)
    if channel.kind == ChannelKind.email:
        assert isinstance(config, EmailChannelConfig)
        await send_via_resend(config.recipient_email, message)
    elif channel.kind == ChannelKind.slack:
        assert isinstance(config, SlackChannelConfig)
        await send_via_slack_webhook(config.webhook_url, message)
    else:
        assert isinstance(config, WebhookChannelConfig)
        await send_via_generic_webhook(config.url, config.secret, message)
