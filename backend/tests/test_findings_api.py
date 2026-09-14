import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.main import app
from app.models.workspace_member import WorkspaceRole
from app.repositories import competitors as competitors_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo


@pytest.fixture
async def two_workspaces(db_session: AsyncSession):
    user_a = await users_repo.create(db_session, clerk_user_id="api-a", email="api-a@example.com", name="A")
    user_b = await users_repo.create(db_session, clerk_user_id="api-b", email="api-b@example.com", name="B")
    workspace_a = await workspaces_repo.create_with_owner(db_session, name="A Co", slug="api-a-co", user_id=user_a.id)
    workspace_b = await workspaces_repo.create_with_owner(db_session, name="B Co", slug="api-b-co", user_id=user_b.id)
    competitor_b = await competitors_repo.create(
        db_session, workspace_b.id, name="Rival", website_url="https://rival.example"
    )
    await db_session.flush()
    return workspace_a, workspace_b, competitor_b, user_a.id


async def test_findings_query_by_other_workspace_competitor_id_returns_404(
    db_session: AsyncSession, two_workspaces
) -> None:
    workspace_a, workspace_b, competitor_b, user_a_id = two_workspaces

    async def override_workspace_context() -> WorkspaceContext:
        return WorkspaceContext(workspace_id=workspace_a.id, user_id=user_a_id, role=WorkspaceRole.owner)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_workspace_context] = override_workspace_context
    from app.db.session import get_db

    app.dependency_overrides[get_db] = override_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/findings?competitor_id={competitor_b.id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
