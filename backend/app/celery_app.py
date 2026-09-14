from celery import Celery

from app.config import settings

celery_app = Celery(
    "compesight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ping",
        "app.tasks.scheduling",
        "app.tasks.crawling",
        "app.tasks.diffing",
    ],
)

celery_app.conf.beat_schedule = {
    "enqueue-due-sources": {
        "task": "enqueue_due_sources",
        "schedule": 15.0,
    },
}
