import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.config import settings
from app.db.session import async_session_factory
from app.models.competitor import Competitor
from app.models.notification_channel import ChannelKind
from app.repositories import digests as digests_repo
from app.repositories import notification_channels as channels_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.notification_channel import EmailChannelConfig
from app.services.channel_crypto import ChannelConfigDecryptionError, decrypt_channel_config
from app.services.delivery.base import AlertMessage, DeliveryFailed
from app.services.delivery.email import send_digest_via_resend
from app.services.digest import assemble_digest

logger = logging.getLogger(__name__)


@celery_app.task(name="enqueue_weekly_digests")
def enqueue_weekly_digests() -> None:
    """Celery-beat entry point, weekly. Not workspace-scoped for the same
    reason app.tasks.scheduling.enqueue_due_sources isn't — a system job
    enumerating every workspace, not a session-derived request."""
    asyncio.run(_enqueue_weekly_digests_async())


async def _enqueue_weekly_digests_async() -> None:
    async with async_session_factory() as db:
        workspaces = await workspaces_repo.list_all(db)

    for workspace in workspaces:
        send_digest_task.delay(str(workspace.id))


@celery_app.task(name="send_digest")
def send_digest_task(workspace_id: str) -> None:
    asyncio.run(_send_digest_async(uuid.UUID(workspace_id)))


async def _send_digest_async(workspace_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        now = datetime.now(timezone.utc)
        period_start, findings = await assemble_digest(db, workspace_id, now)
        digest = await digests_repo.create_if_absent(
            db, workspace_id, period_start, now, [f.id for f in findings]
        )
        await db.commit()

        if digest is None:
            # A redelivered or manually retried task for a period already
            # recorded — the earlier run owns sending it.
            return

        if not findings:
            # A genuinely quiet period — still recorded so the next run's
            # window starts from here, but nothing to email.
            await digests_repo.mark_sent(db, digest, datetime.now(timezone.utc))
            await db.commit()
            return

        email_channels = [
            c for c in await channels_repo.list_for_workspace(db, workspace_id) if c.kind == ChannelKind.email
        ]
        if not email_channels:
            await digests_repo.mark_sent(db, digest, datetime.now(timezone.utc))
            await db.commit()
            return

        messages = []
        for finding in findings:
            competitor = await db.get(Competitor, finding.competitor_id)
            competitor_name = competitor.name if competitor is not None else "A competitor"
            detail_url = f"{settings.dashboard_base_url}/competitors/{finding.competitor_id}/findings/{finding.id}"
            messages.append(AlertMessage.from_finding(finding, competitor_name, detail_url))

        period_label = f"{period_start.date().isoformat()} to {now.date().isoformat()}"
        for channel in email_channels:
            try:
                config = decrypt_channel_config(channel.config)
                assert isinstance(config, EmailChannelConfig)
                await send_digest_via_resend(config.recipient_email, period_label, messages)
            except (DeliveryFailed, ChannelConfigDecryptionError) as exc:
                # One channel failing must not stop the others, and must
                # not leave the digest row unmarked forever — the finding
                # set is already durable in `digest.finding_ids`
                # (docs/rules.md: silence is never success; delivery
                # failures are logged, not raised past this boundary).
                logger.warning("digest delivery failed for channel %s: %s", channel.id, exc)

        await digests_repo.mark_sent(db, digest, datetime.now(timezone.utc))
        await db.commit()
