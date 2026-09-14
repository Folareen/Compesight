import random

from app.config import settings


def backoff_with_jitter(attempt: int) -> float:
    """Exponential backoff with jitter, in seconds. `attempt` is 1-indexed
    (the first retry passes 1). Never lets one bad source retry instantly
    and stall the queue behind it."""
    base = settings.crawl_backoff_base_seconds * (2 ** (attempt - 1))
    capped = min(base, settings.crawl_backoff_cap_seconds)
    return capped + random.uniform(0, settings.crawl_backoff_jitter_seconds)
