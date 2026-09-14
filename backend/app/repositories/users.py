from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_clerk_id(db: AsyncSession, clerk_user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, clerk_user_id: str, email: str, name: str | None) -> User:
    user = User(clerk_user_id=clerk_user_id, email=email, name=name)
    db.add(user)
    await db.flush()
    return user
