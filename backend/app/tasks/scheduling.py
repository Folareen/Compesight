import asyncio
import random
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.celery_app import celery_app
from app.config import settings
from app.db.session import async_session_factory
from app.repositories import sources as sources_repo
from app.tasks.crawling import crawl_source_task

_DUE_SOURCES_LIMIT = 200

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url)
    return _redis


@celery_app.task(name="enqueue_due_sources")
def enqueue_due_sources() -> None:
    """Celery-beat entry point. Enqueues crawl_source for every source due
    for a scheduled crawl, with jitter and a lock so a source is never
    enqueued twice concurrently. Not workspace-scoped — see the docstring
    on repositories.sources.get_due_for_crawl for why that's correct here."""
    asyncio.run(_enqueue_due_sources_async())


async def _enqueue_due_sources_async() -> None:
    redis = _get_redis()
    async with async_session_factory() as db:
        due_sources = await sources_repo.get_due_for_crawl(db, datetime.now(timezone.utc), _DUE_SOURCES_LIMIT)

    for source in due_sources:
        lock_key = f"crawl:source_lock:{source.id}"
        acquired = await redis.set(lock_key, "1", nx=True, ex=settings.source_lock_ttl_seconds)
        if not acquired:
            # Already running (or a lock from a very recent enqueue) —
            # skip rather than double-enqueue; the next tick picks it up.
            continue

        jitter = random.uniform(0, settings.scheduler_enqueue_jitter_seconds)
        crawl_source_task.apply_async(args=[str(source.id)], countdown=jitter)
