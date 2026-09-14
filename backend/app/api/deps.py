import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.workspace_member import WorkspaceRole
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.services.clerk_auth import InvalidSessionToken, verify_session_token

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class WorkspaceContext:
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceRole


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing session token")

    try:
        claims = verify_session_token(credentials.credentials)
    except InvalidSessionToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session token") from exc

    user = await users_repo.get_by_clerk_id(db, claims.clerk_user_id)
    if user is None:
        user = await users_repo.create(db, claims.clerk_user_id, claims.email, claims.name)
        await db.commit()
    return user


async def get_workspace_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceContext:
    membership = await workspaces_repo.get_first_membership_for_user(db, user.id)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no workspace for this user")

    return WorkspaceContext(
        workspace_id=membership.workspace_id, user_id=user.id, role=membership.role
    )
