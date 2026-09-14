from datetime import datetime, timezone

from app.models.source import SourceStatus
from app.services.crawl_outcome import CrawlOutcome
from app.services.source_health import next_health_state


def _outcome(*, http_status: int | None, error: str | None = None) -> CrawlOutcome:
    return CrawlOutcome(
        fetched_at=datetime.now(timezone.utc),
        content_hash=None,
        raw_payload=None,
        http_status=http_status,
        error=error,
    )


def test_success_resets_to_healthy() -> None:
    status, failures, reason = next_health_state(
        SourceStatus.degraded, 2, _outcome(http_status=200)
    )
    assert status == SourceStatus.healthy
    assert failures == 0
    assert reason is None


def test_first_failure_degrades() -> None:
    status, failures, reason = next_health_state(
        SourceStatus.healthy, 0, _outcome(http_status=500, error="server error")
    )
    assert status == SourceStatus.degraded
    assert failures == 1


def test_escalates_to_failing_after_threshold() -> None:
    status, failures, reason = next_health_state(
        SourceStatus.degraded, 2, _outcome(http_status=500, error="server error")
    )
    assert status == SourceStatus.failing
    assert failures == 3


def test_sustained_403_blocks() -> None:
    status, failures, reason = next_health_state(
        SourceStatus.degraded, 1, _outcome(http_status=403, error="forbidden")
    )
    assert status == SourceStatus.blocked
    assert reason is not None


def test_single_403_does_not_block_yet() -> None:
    status, failures, reason = next_health_state(
        SourceStatus.healthy, 0, _outcome(http_status=403, error="forbidden")
    )
    assert status == SourceStatus.degraded


def test_blocked_never_auto_clears() -> None:
    status, failures, reason = next_health_state(
        SourceStatus.blocked, 5, _outcome(http_status=200)
    )
    assert status == SourceStatus.blocked
