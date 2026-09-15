from celery import Celery
from celery.schedules import crontab

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
        "app.tasks.routing",
        "app.tasks.delivery",
        "app.tasks.digest",
    ],
)

celery_app.conf.beat_schedule = {
    "enqueue-due-sources": {
        "task": "enqueue_due_sources",
        "schedule": 15.0,
    },
    "enqueue-weekly-digests": {
        "task": "enqueue_weekly_digests",
        "schedule": crontab(day_of_week=1, hour=9, minute=0),
    },
}
