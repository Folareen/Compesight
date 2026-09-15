from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# NullPool: this engine is a process-wide singleton, but Celery tasks each
# run their own event loop (one `asyncio.run` per task — see
# docs/backend-rules.md). A pooled asyncpg connection is bound to the loop
# it was created on, so reusing one across tasks raises "got Future ...
# attached to a different loop". NullPool opens a fresh connection per
# checkout instead of reusing one across loop boundaries.
engine = create_async_engine(settings.database_url, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
