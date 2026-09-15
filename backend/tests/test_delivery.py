import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx

from app.config import settings
from app.db.session import async_session_factory
from app.models.alert import Alert, AlertStatus
from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.notification_channel import ChannelKind
from app.models.source import SourceType
from app.repositories import alerts as alerts_repo
from app.repositories import competitors as competitors_repo
from app.repositories import findings as findings_repo
from app.repositories import notification_channels as channels_repo
from app.repositories import snapshots as snapshots_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.notification_channel import SlackChannelConfig
from app.services.channel_crypto import encrypt_channel_config
from app.tasks.delivery import _deliver_alert_async


async def _setup_alert():
    unique = uuid.uuid4().hex[:8]
    async with async_session_factory() as db:
        user = await users_repo.create(
            db, clerk_user_id=f"deliver-user-{unique}", email=f"deliver-{unique}@example.com", name="D"
        )
        workspace = await workspaces_repo.create_with_owner(
            db, name="Deliver Co", slug=f"deliver-co-{unique}", user_id=user.id
        )
        competitor = await competitors_repo.create(
            db, workspace.id, name="Rival", website_url="https://rival.example"
        )
        source = await sources_repo.create(
            db, workspace.id, competitor.id, SourceType.pricing_page, "https://rival.example/pricing", {}, 3600
        )
        snapshot = await snapshots_repo.create(
            db, workspace.id, source.id, datetime.now(timezone.utc), "hash", "<html></html>", 200, None
        )
        channel = await channels_repo.create(
            db,
            workspace.id,
            ChannelKind.slack,
            encrypt_channel_config(SlackChannelConfig(webhook_url="https://hooks.slack.example/x")),
        )
        finding = await findings_repo.create(
            db,
            workspace.id,
            competitor.id,
            source.id,
            snapshot.id,
            ChangeType.pricing,
            Urgency.high,
            "Pricing changed",
            "Pro tier changed",
            {"fields": []},
            False,
            f"dedupe-{unique}",
            ClassificationStatus.ok,
        )
        alert = await alerts_repo.create_if_absent(db, workspace.id, finding.id, channel.id)
        await db.commit()
    return alert.id


def _http_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=httpx.Request("POST", "https://hooks.slack.example/x"))


async def test_successful_delivery_marks_alert_sent() -> None:
    alert_id = await _setup_alert()

    mock_post = AsyncMock(return_value=_http_response(200))
    with patch("httpx.AsyncClient.post", mock_post):
        retry_after = await _deliver_alert_async(alert_id, retries_so_far=0)

    assert retry_after is None
    async with async_session_factory() as db:
        alert = await db.get(Alert, alert_id)
    assert alert.status == AlertStatus.sent
    assert alert.sent_at is not None


async def test_failed_delivery_before_max_retries_schedules_retry() -> None:
    alert_id = await _setup_alert()

    mock_post = AsyncMock(side_effect=httpx.ConnectTimeout("boom"))
    with patch("httpx.AsyncClient.post", mock_post):
        retry_after = await _deliver_alert_async(alert_id, retries_so_far=0)

    assert retry_after is not None
    assert retry_after > 0
    async with async_session_factory() as db:
        alert = await db.get(Alert, alert_id)
    assert alert.status == AlertStatus.pending
    assert alert.attempts == 1
    assert alert.last_error is not None


async def test_failed_delivery_at_max_retries_marks_failed_and_stops() -> None:
    alert_id = await _setup_alert()

    mock_post = AsyncMock(side_effect=httpx.ConnectTimeout("boom"))
    with patch("httpx.AsyncClient.post", mock_post):
        retry_after = await _deliver_alert_async(alert_id, retries_so_far=settings.alert_delivery_max_retries)

    assert retry_after is None
    async with async_session_factory() as db:
        alert = await db.get(Alert, alert_id)
    assert alert.status == AlertStatus.failed
    assert alert.last_error is not None
