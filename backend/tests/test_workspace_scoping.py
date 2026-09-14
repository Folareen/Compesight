import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_member import WorkspaceMember
from app.repositories.scoped import get_scoped_or_404
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo


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
