from app.models.source import SourceStatus
from app.services.crawl_outcome import CrawlOutcome

_BLOCKED_STATUS_CODES = {403, 429}
_SUSTAINED_BLOCK_THRESHOLD = 2
_FAILING_THRESHOLD = 3


def next_health_state(
    current: SourceStatus, consecutive_failures: int, outcome: CrawlOutcome
) -> tuple[SourceStatus, int, str | None]:
    """Pure state-machine step. Returns (new_status, new_consecutive_failures,
    blocked_reason) — blocked_reason is None unless this call is the one
    transitioning the source into `blocked`; the caller keeps the source's
    existing blocked_reason for every other outcome.

    Never auto-clears `blocked` — that's terminal until a human action or a
    much slower re-probe (out of scope this phase); a source already
    blocked stays blocked regardless of `outcome`."""
    if current == SourceStatus.blocked:
        return SourceStatus.blocked, consecutive_failures, None

    if outcome.error is None and outcome.http_status is not None and 200 <= outcome.http_status < 300:
        return SourceStatus.healthy, 0, None

    failures = consecutive_failures + 1

    if outcome.http_status in _BLOCKED_STATUS_CODES and failures >= _SUSTAINED_BLOCK_THRESHOLD:
        return SourceStatus.blocked, failures, f"received {outcome.http_status} repeatedly"

    if failures >= _FAILING_THRESHOLD:
        return SourceStatus.failing, failures, None

    return SourceStatus.degraded, failures, None
