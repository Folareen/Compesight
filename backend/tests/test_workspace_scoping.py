import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.source import SourceType
from app.models.workspace_member import WorkspaceMember
from app.repositories import competitors as competitors_repo
from app.repositories import findings as findings_repo
from app.repositories import snapshots as snapshots_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.repositories.scoped import get_scoped_or_404


async def test_workspace_a_cannot_read_workspace_b_resource(db_session: AsyncSession) -> None:
    user_a = await users_repo.create(db_session, clerk_user_id="clerk_a", email="a@example.com", name="A")
    user_b = await users_repo.create(db_session, clerk_user_id="clerk_b", email="b@example.com", name="B")

    workspace_a = await workspaces_repo.create_with_owner(db_session, name="A Co", slug="a-co", user_id=user_a.id)
    workspace_b = await workspaces_repo.create_with_owner(db_session, name="B Co", slug="b-co", user_id=user_b.id)
    await db_session.flush()

    membership_b = await workspaces_repo.get_first_membership_for_user(db_session, user_b.id)
    assert membership_b is not None

    # membership_b's id is an untrusted claim when checked against A's workspace context.
    result = await get_scoped_or_404(db_session, WorkspaceMember, workspace_a.id, membership_b.id)

    assert result is None


async def test_workspace_a_can_read_its_own_resource(db_session: AsyncSession) -> None:
    user = await users_repo.create(db_session, clerk_user_id="clerk_c", email="c@example.com", name="C")
    workspace = await workspaces_repo.create_with_owner(db_session, name="C Co", slug="c-co", user_id=user.id)
    await db_session.flush()

    membership = await workspaces_repo.get_first_membership_for_user(db_session, user.id)
    assert membership is not None

    result = await get_scoped_or_404(db_session, WorkspaceMember, workspace.id, membership.id)

    assert result is not None
    assert result.id == membership.id


async def test_nonexistent_resource_id_returns_none(db_session: AsyncSession) -> None:
    user = await users_repo.create(db_session, clerk_user_id="clerk_d", email="d@example.com", name="D")
    workspace = await workspaces_repo.create_with_owner(db_session, name="D Co", slug="d-co", user_id=user.id)
    await db_session.flush()

    result = await get_scoped_or_404(db_session, WorkspaceMember, workspace.id, uuid.uuid4())

    assert result is None


async def test_workspace_a_cannot_read_workspace_b_competitor(db_session: AsyncSession) -> None:
    user_a = await users_repo.create(db_session, clerk_user_id="clerk_e", email="e@example.com", name="E")
    user_b = await users_repo.create(db_session, clerk_user_id="clerk_f", email="f@example.com", name="F")
    workspace_a = await workspaces_repo.create_with_owner(db_session, name="E Co", slug="e-co", user_id=user_a.id)
    workspace_b = await workspaces_repo.create_with_owner(db_session, name="F Co", slug="f-co", user_id=user_b.id)

    competitor_b = await competitors_repo.create(
        db_session, workspace_b.id, name="Rival", website_url="https://rival.example"
    )
    await db_session.flush()

    result = await competitors_repo.get(db_session, workspace_a.id, competitor_b.id)

    assert result is None


async def test_workspace_a_cannot_read_workspace_b_source(db_session: AsyncSession) -> None:
    user_a = await users_repo.create(db_session, clerk_user_id="clerk_g", email="g@example.com", name="G")
    user_b = await users_repo.create(db_session, clerk_user_id="clerk_h", email="h@example.com", name="H")
    workspace_a = await workspaces_repo.create_with_owner(db_session, name="G Co", slug="g-co", user_id=user_a.id)
    workspace_b = await workspaces_repo.create_with_owner(db_session, name="H Co", slug="h-co", user_id=user_b.id)

    competitor_b = await competitors_repo.create(
        db_session, workspace_b.id, name="Rival", website_url="https://rival.example"
    )
    source_b = await sources_repo.create(
        db_session,
        workspace_b.id,
        competitor_b.id,
        SourceType.pricing_page,
        "https://rival.example/pricing",
        {},
        3600,
    )
    await db_session.flush()

    result = await sources_repo.get(db_session, workspace_a.id, source_b.id)

    assert result is None


async def test_workspace_a_findings_list_never_returns_workspace_b_rows(db_session: AsyncSession) -> None:
    user_a = await users_repo.create(db_session, clerk_user_id="clerk_i", email="i@example.com", name="I")
    user_b = await users_repo.create(db_session, clerk_user_id="clerk_j", email="j@example.com", name="J")
    workspace_a = await workspaces_repo.create_with_owner(db_session, name="I Co", slug="i-co", user_id=user_a.id)
    workspace_b = await workspaces_repo.create_with_owner(db_session, name="J Co", slug="j-co", user_id=user_b.id)

    competitor_b = await competitors_repo.create(
        db_session, workspace_b.id, name="Rival", website_url="https://rival.example"
    )
    source_b = await sources_repo.create(
        db_session,
        workspace_b.id,
        competitor_b.id,
        SourceType.pricing_page,
        "https://rival.example/pricing",
        {},
        3600,
    )
    await db_session.flush()

    snapshot_b = await snapshots_repo.create(
        db_session, workspace_b.id, source_b.id, datetime.now(timezone.utc), "hash", "<html></html>", 200, None
    )
    await db_session.flush()

    finding_b = await findings_repo.create(
        db_session,
        workspace_b.id,
        competitor_b.id,
        source_b.id,
        snapshot_b.id,
        ChangeType.pricing,
        Urgency.medium,
        "Pricing changed",
        "Pro tier changed",
        {"fields": []},
        False,
        "dedupe-b-1",
        ClassificationStatus.ok,
    )
    await db_session.flush()

    findings_a, _ = await findings_repo.list_for_workspace(db_session, workspace_a.id)
    assert findings_a == []

    # Guessing workspace B's competitor_id from workspace A's context must not leak B's findings.
    findings_a_filtered, _ = await findings_repo.list_for_workspace(
        db_session, workspace_a.id, competitor_id=competitor_b.id
    )
    assert findings_a_filtered == []

    direct_get = await findings_repo.get(db_session, workspace_a.id, finding_b.id)
    assert direct_get is None
