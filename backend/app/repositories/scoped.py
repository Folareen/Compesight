import uuid
from typing import TypeVar

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


def workspace_scoped(stmt: Select[tuple[ModelT]], model: type[ModelT], workspace_id: uuid.UUID) -> Select[tuple[ModelT]]:
    """The one place a workspace-scoped query is filtered.

    Every repository function touching a workspace-scoped table builds its
    query through this helper instead of writing `.where(Model.workspace_id == ...)`
    inline, so there is exactly one line to audit for rule 1 (see docs/rules.md).
    `workspace_id` is a required positional argument on purpose — it must come
    from the caller's verified session, never from a request.
    """
    return stmt.where(model.workspace_id == workspace_id)


async def get_scoped_or_404(
    db: AsyncSession, model: type[ModelT], workspace_id: uuid.UUID, resource_id: uuid.UUID
) -> ModelT | None:
    """Fetch a workspace-scoped row by id, or None if it doesn't belong to this workspace.

    Callers must turn a None into a 404, never a 403 — a resource id in a URL
    is an untrusted claim until checked against the session's workspace, and
    confirming existence to the wrong workspace is a cross-tenant leak.
    """
    stmt = workspace_scoped(
        Select(model).where(model.id == resource_id), model, workspace_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
