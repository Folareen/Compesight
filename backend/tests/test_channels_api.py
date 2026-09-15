import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.main import app
from app.models.workspace_member import WorkspaceRole
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo


@pytest.fixture
async def two_workspaces(db_session: AsyncSession):
    unique = uuid.uuid4().hex[:8]
    user_a = await users_repo.create(
        db_session, clerk_user_id=f"ch-a-{unique}", email=f"ch-a-{unique}@example.com", name="A"
    )
    user_b = await users_repo.create(
        db_session, clerk_user_id=f"ch-b-{unique}", email=f"ch-b-{unique}@example.com", name="B"
    )
    workspace_a = await workspaces_repo.create_with_owner(
        db_session, name="A Co", slug=f"ch-a-co-{unique}", user_id=user_a.id
    )
    workspace_b = await workspaces_repo.create_with_owner(
        db_session, name="B Co", slug=f"ch-b-co-{unique}", user_id=user_b.id
    )
    await db_session.flush()
    return workspace_a, workspace_b, user_a.id, user_b.id


async def _request(db_session: AsyncSession, workspace_id, user_id, method: str, url: str, json: dict | None = None):
    async def override_workspace_context() -> WorkspaceContext:
        return WorkspaceContext(workspace_id=workspace_id, user_id=user_id, role=WorkspaceRole.owner)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_workspace_context] = override_workspace_context
    app.dependency_overrides[get_db] = override_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, json=json)
    finally:
        app.dependency_overrides.clear()


async def test_created_channel_never_returns_raw_webhook_url(db_session: AsyncSession, two_workspaces) -> None:
    workspace_a, _workspace_b, user_a_id, _user_b_id = two_workspaces

    response = await _request(
        db_session,
        workspace_a.id,
        user_a_id,
        "POST",
        "/api/channels",
        {"config": {"kind": "slack", "webhook_url": "https://hooks.slack.example/services/SECRETPATH123"}},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["display_identifier"] != "https://hooks.slack.example/services/SECRETPATH123"


async def test_workspace_b_cannot_list_workspace_a_channels(db_session: AsyncSession, two_workspaces) -> None:
    workspace_a, workspace_b, user_a_id, user_b_id = two_workspaces

    create_response = await _request(
        db_session,
        workspace_a.id,
        user_a_id,
        "POST",
        "/api/channels",
        {"config": {"kind": "webhook", "url": "https://example.com/hook", "secret": None}},
    )
    assert create_response.status_code == 201

    list_response = await _request(db_session, workspace_b.id, user_b_id, "GET", "/api/channels")
    assert list_response.status_code == 200
    assert list_response.json() == []


async def test_workspace_b_deleting_workspace_a_channel_returns_404(
    db_session: AsyncSession, two_workspaces
) -> None:
    workspace_a, workspace_b, user_a_id, user_b_id = two_workspaces

    create_response = await _request(
        db_session,
        workspace_a.id,
        user_a_id,
        "POST",
        "/api/channels",
        {"config": {"kind": "email", "recipient_email": "team@rival.example"}},
    )
    channel_id = create_response.json()["id"]

    delete_response = await _request(
        db_session, workspace_b.id, user_b_id, "DELETE", f"/api/channels/{channel_id}"
    )
    assert delete_response.status_code == 404
