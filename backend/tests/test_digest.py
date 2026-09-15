import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.digest import Digest
from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.notification_channel import ChannelKind
from app.models.source import SourceType
from app.repositories import competitors as competitors_repo
from app.repositories import findings as findings_repo
from app.repositories import notification_channels as channels_repo
from app.repositories import snapshots as snapshots_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.notification_channel import EmailChannelConfig
from app.services.channel_crypto import encrypt_channel_config
from app.tasks.digest import _send_digest_async


async def _setup(with_email_channel: bool):
    unique = uuid.uuid4().hex[:8]
    async with async_session_factory() as db:
        user = await users_repo.create(
            db, clerk_user_id=f"digest-user-{unique}", email=f"digest-{unique}@example.com", name="Dg"
        )
        workspace = await workspaces_repo.create_with_owner(
            db, name="Digest Co", slug=f"digest-co-{unique}", user_id=user.id
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
        await findings_repo.create(
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
        if with_email_channel:
            await channels_repo.create(
                db,
                workspace.id,
                ChannelKind.email,
                encrypt_channel_config(EmailChannelConfig(recipient_email="team@example.com")),
            )
        await db.commit()
    return workspace


async def test_digest_with_findings_sends_email_and_records_finding_ids() -> None:
    workspace = await _setup(with_email_channel=True)

    with patch("app.tasks.digest.send_digest_via_resend", new=AsyncMock()) as mock_send:
        await _send_digest_async(workspace.id)

    mock_send.assert_awaited_once()
    async with async_session_factory() as fresh_db:
        digests = (
            (await fresh_db.execute(select(Digest).where(Digest.workspace_id == workspace.id))).scalars().all()
        )
    assert len(digests) == 1
    assert len(digests[0].finding_ids) == 1
    assert digests[0].sent_at is not None


async def test_digest_with_no_email_channel_records_but_does_not_send() -> None:
    workspace = await _setup(with_email_channel=False)

    with patch("app.tasks.digest.send_digest_via_resend", new=AsyncMock()) as mock_send:
        await _send_digest_async(workspace.id)

    mock_send.assert_not_awaited()
    async with async_session_factory() as fresh_db:
        digests = (
            (await fresh_db.execute(select(Digest).where(Digest.workspace_id == workspace.id))).scalars().all()
        )
    assert len(digests) == 1
    assert digests[0].sent_at is not None


async def test_second_digest_run_only_covers_findings_since_the_first() -> None:
    workspace = await _setup(with_email_channel=True)

    with patch("app.tasks.digest.send_digest_via_resend", new=AsyncMock()):
        await _send_digest_async(workspace.id)  # covers the one finding created in setup

    async with async_session_factory() as db:
        # A finding created after the first digest's period_end.
        competitor = (await competitors_repo.list_for_workspace(db, workspace.id))[0]
        source = (await sources_repo.list_for_competitor(db, workspace.id, competitor.id))[0]
        snapshot = await snapshots_repo.create(
            db, workspace.id, source.id, datetime.now(timezone.utc), "hash2", "<html></html>", 200, None
        )
        await findings_repo.create(
            db,
            workspace.id,
            source.competitor_id,
            source.id,
            snapshot.id,
            ChangeType.pricing,
            Urgency.medium,
            "Second change",
            "Another change",
            {"fields": []},
            False,
            f"dedupe-second-{uuid.uuid4().hex[:8]}",
            ClassificationStatus.ok,
        )
        await db.commit()

    with patch("app.tasks.digest.send_digest_via_resend", new=AsyncMock()) as mock_send:
        await _send_digest_async(workspace.id)

    mock_send.assert_awaited_once()
    async with async_session_factory() as fresh_db:
        digests = (
            (await fresh_db.execute(select(Digest).where(Digest.workspace_id == workspace.id)))
            .scalars()
            .all()
        )
    assert len(digests) == 2
    second_digest = max(digests, key=lambda d: d.created_at)
    assert len(second_digest.finding_ids) == 1
