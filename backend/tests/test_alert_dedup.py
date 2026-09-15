import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.alert import Alert
from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.notification_channel import ChannelKind
from app.models.source import SourceType
from app.repositories import alerts as alerts_repo
from app.repositories import competitors as competitors_repo
from app.repositories import findings as findings_repo
from app.repositories import notification_channels as channels_repo
from app.repositories import routing_rules as routing_rules_repo
from app.repositories import snapshots as snapshots_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.notification_channel import WebhookChannelConfig
from app.services.channel_crypto import encrypt_channel_config
from app.tasks.routing import _route_finding_async


async def _setup(db: AsyncSession):
    unique = uuid.uuid4().hex[:8]
    user = await users_repo.create(
        db, clerk_user_id=f"route-user-{unique}", email=f"route-{unique}@example.com", name="R"
    )
    workspace = await workspaces_repo.create_with_owner(
        db, name="Route Co", slug=f"route-co-{unique}", user_id=user.id
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
        ChannelKind.webhook,
        encrypt_channel_config(WebhookChannelConfig(url="https://example.com/hook", secret=None)),
    )
    await routing_rules_repo.replace_for_workspace(
        db, workspace.id, [(None, None, Urgency.low, [channel.id], True)]
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
    await db.commit()
    return workspace, finding, channel


async def test_routing_twice_creates_exactly_one_alert_per_channel() -> None:
    async with async_session_factory() as setup_db:
        workspace, finding, channel = await _setup(setup_db)

    with patch("app.tasks.routing.deliver_alert_task.delay"):
        await _route_finding_async(finding.id)
        await _route_finding_async(finding.id)  # retried routing pass, e.g. task redelivery

    async with async_session_factory() as fresh_db:
        alerts = (
            (await fresh_db.execute(select(Alert).where(Alert.finding_id == finding.id))).scalars().all()
        )

    assert len(alerts) == 1
    assert alerts[0].channel_id == channel.id


async def test_create_if_absent_is_a_no_op_on_conflict(db_session: AsyncSession) -> None:
    workspace, finding, channel = await _setup(db_session)

    first = await alerts_repo.create_if_absent(db_session, workspace.id, finding.id, channel.id)
    second = await alerts_repo.create_if_absent(db_session, workspace.id, finding.id, channel.id)

    assert first is not None
    assert second is None
