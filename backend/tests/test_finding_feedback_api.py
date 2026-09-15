import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.main import app
from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.workspace_member import WorkspaceRole
from app.repositories import competitors as competitors_repo
from app.repositories import findings as findings_repo
from app.repositories import snapshots as snapshots_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.repositories.finding_feedback import recent_for_prompt


@pytest.fixture
async def workspace_with_finding(db_session: AsyncSession):
    from app.models.source import SourceType

    unique = uuid.uuid4().hex[:8]
    user_a = await users_repo.create(
        db_session, clerk_user_id=f"fb-a-{unique}", email=f"fb-a-{unique}@example.com", name="A"
    )
    user_b = await users_repo.create(
        db_session, clerk_user_id=f"fb-b-{unique}", email=f"fb-b-{unique}@example.com", name="B"
    )
    workspace_a = await workspaces_repo.create_with_owner(
        db_session, name="A Co", slug=f"fb-a-co-{unique}", user_id=user_a.id
    )
    workspace_b = await workspaces_repo.create_with_owner(
        db_session, name="B Co", slug=f"fb-b-co-{unique}", user_id=user_b.id
    )

    competitor = await competitors_repo.create(
        db_session, workspace_a.id, name="Rival", website_url="https://rival.example"
    )
    source = await sources_repo.create(
        db_session, workspace_a.id, competitor.id, SourceType.pricing_page, "https://rival.example/pricing", {}, 3600
    )
    snapshot = await snapshots_repo.create(
        db_session, workspace_a.id, source.id, datetime.now(timezone.utc), "hash", "<html></html>", 200, None
    )
    finding = await findings_repo.create(
        db_session,
        workspace_a.id,
        competitor.id,
        source.id,
        snapshot.id,
        ChangeType.pricing,
        Urgency.medium,
        "Pricing changed",
        "Pro tier changed",
        {"fields": []},
        False,
        "dedupe-fb-1",
        ClassificationStatus.ok,
    )
    await db_session.flush()
    return workspace_a, workspace_b, finding, user_a.id


async def _post_feedback(db_session: AsyncSession, workspace_id, user_id, finding_id, body: dict):
    async def override_workspace_context() -> WorkspaceContext:
        return WorkspaceContext(workspace_id=workspace_id, user_id=user_id, role=WorkspaceRole.owner)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_workspace_context] = override_workspace_context
    app.dependency_overrides[get_db] = override_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(f"/api/findings/{finding_id}/feedback", json=body)
    finally:
        app.dependency_overrides.clear()


async def test_feedback_persists_and_is_retrievable_for_prompt(
    db_session: AsyncSession, workspace_with_finding
) -> None:
    workspace_a, _workspace_b, finding, user_a_id = workspace_with_finding

    response = await _post_feedback(
        db_session,
        workspace_a.id,
        user_a_id,
        finding.id,
        {"verdict": "noise", "corrected_change_type": "content", "corrected_urgency": "low"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["verdict"] == "noise"
    assert body["corrected_change_type"] == "content"

    examples = await recent_for_prompt(db_session, workspace_a.id)
    assert len(examples) == 1
    assert examples[0].finding_id == finding.id


async def test_feedback_on_another_workspaces_finding_returns_404(
    db_session: AsyncSession, workspace_with_finding
) -> None:
    _workspace_a, workspace_b, finding, _user_a_id = workspace_with_finding
    unique = uuid.uuid4().hex[:8]
    user_b = await users_repo.create(
        db_session, clerk_user_id=f"fb-b2-{unique}", email=f"fb-b2-{unique}@example.com", name="B2"
    )
    await db_session.flush()

    response = await _post_feedback(
        db_session, workspace_b.id, user_b.id, finding.id, {"verdict": "useful"}
    )

    assert response.status_code == 404
