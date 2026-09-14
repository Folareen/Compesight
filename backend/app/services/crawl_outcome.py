from datetime import datetime

from pydantic import BaseModel


class CrawlOutcome(BaseModel):
    """Result of one crawl attempt. `error` set means the attempt failed —
    this is expected, not exceptional (docs/scraping.md); it is never
    raised as an exception by the crawler service. RobotsDisallowed is the
    one crawl-time condition that IS raised, because `blocked` is a
    different, terminal state that must not be confused with an ordinary
    retryable failure."""

    fetched_at: datetime
    content_hash: str | None
    raw_payload: str | None
    http_status: int | None
    error: str | None
