import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.repositories import workspaces as workspaces_repo


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workspace"


async def bootstrap_workspace(db: AsyncSession, user_id: uuid.UUID, name: str) -> Workspace:
    """Create the single workspace a newly signed-up user lands in.

    Appends a short suffix of the user id to the slug so two workspaces
    named the same thing don't collide on the unique slug constraint.
    """
    base_slug = _slugify(name)
    slug = f"{base_slug}-{str(user_id)[:8]}"
    return await workspaces_repo.create_with_owner(db, name=name, slug=slug, user_id=user_id)
