import uuid
from datetime import datetime, timedelta, timezone

from app.models.competitor import Competitor, CompetitorStatus
from app.models.finding import ChangeType, Urgency
from app.models.routing_rule import RoutingRule
from app.services.routing import is_muted, resolve_channels

_COMPETITOR_ID = uuid.uuid4()
_OTHER_COMPETITOR_ID = uuid.uuid4()
_WORKSPACE_ID = uuid.uuid4()


def _rule(
    *, competitor_id=None, change_type=None, min_urgency=Urgency.low, channels=None, enabled=True
) -> RoutingRule:
    return RoutingRule(
        id=uuid.uuid4(),
        workspace_id=_WORKSPACE_ID,
        competitor_id=competitor_id,
        change_type=change_type,
        min_urgency=min_urgency,
        channels=channels or [uuid.uuid4()],
        enabled=enabled,
    )


def test_competitor_and_type_beats_every_other_specificity() -> None:
    most_specific = _rule(
        competitor_id=_COMPETITOR_ID, change_type=ChangeType.pricing, channels=[uuid.UUID(int=1)]
    )
    competitor_only = _rule(competitor_id=_COMPETITOR_ID, channels=[uuid.UUID(int=2)])
    workspace_and_type = _rule(change_type=ChangeType.pricing, channels=[uuid.UUID(int=3)])
    workspace_default = _rule(channels=[uuid.UUID(int=4)])

    candidates = [workspace_default, workspace_and_type, competitor_only, most_specific]

    result = resolve_channels(candidates, _COMPETITOR_ID, ChangeType.pricing, Urgency.high)

    assert result == [uuid.UUID(int=1)]


def test_competitor_only_beats_workspace_and_type() -> None:
    competitor_only = _rule(competitor_id=_COMPETITOR_ID, channels=[uuid.UUID(int=2)])
    workspace_and_type = _rule(change_type=ChangeType.pricing, channels=[uuid.UUID(int=3)])

    result = resolve_channels(
        [workspace_and_type, competitor_only], _COMPETITOR_ID, ChangeType.pricing, Urgency.high
    )

    assert result == [uuid.UUID(int=2)]


def test_workspace_and_type_beats_workspace_default() -> None:
    workspace_and_type = _rule(change_type=ChangeType.pricing, channels=[uuid.UUID(int=3)])
    workspace_default = _rule(channels=[uuid.UUID(int=4)])

    result = resolve_channels(
        [workspace_default, workspace_and_type], _COMPETITOR_ID, ChangeType.pricing, Urgency.high
    )

    assert result == [uuid.UUID(int=3)]


def test_no_matching_rule_returns_no_channels() -> None:
    rule_for_other_competitor = _rule(competitor_id=_OTHER_COMPETITOR_ID)

    result = resolve_channels([rule_for_other_competitor], _COMPETITOR_ID, ChangeType.pricing, Urgency.high)

    assert result == []


def test_disabled_rule_is_never_a_candidate_in_practice() -> None:
    # resolve_channels trusts its candidate list (enabled filtering happens
    # in the repository query) — this documents that an enabled=False rule
    # passed in anyway still matches, i.e. enforcement is the repository's
    # job, not this function's.
    disabled = _rule(enabled=False, channels=[uuid.UUID(int=9)])

    result = resolve_channels([disabled], _COMPETITOR_ID, ChangeType.pricing, Urgency.high)

    assert result == [uuid.UUID(int=9)]


def test_urgency_below_threshold_suppresses_alert() -> None:
    rule = _rule(min_urgency=Urgency.high, channels=[uuid.UUID(int=5)])

    result = resolve_channels([rule], _COMPETITOR_ID, ChangeType.pricing, Urgency.medium)

    assert result == []


def test_urgency_at_or_above_threshold_alerts() -> None:
    rule = _rule(min_urgency=Urgency.medium, channels=[uuid.UUID(int=6)])

    assert resolve_channels([rule], _COMPETITOR_ID, ChangeType.pricing, Urgency.medium) == [uuid.UUID(int=6)]
    assert resolve_channels([rule], _COMPETITOR_ID, ChangeType.pricing, Urgency.high) == [uuid.UUID(int=6)]


def _competitor(status: CompetitorStatus, muted_until: datetime | None = None) -> Competitor:
    return Competitor(
        id=_COMPETITOR_ID,
        workspace_id=_WORKSPACE_ID,
        name="Rival",
        website_url="https://rival.example",
        status=status,
        muted_until=muted_until,
    )


def test_active_competitor_is_never_muted() -> None:
    competitor = _competitor(CompetitorStatus.active)
    assert is_muted(competitor, datetime.now(timezone.utc)) is False


def test_muted_with_no_expiry_is_muted_indefinitely() -> None:
    competitor = _competitor(CompetitorStatus.muted, muted_until=None)
    assert is_muted(competitor, datetime.now(timezone.utc)) is True


def test_muted_until_future_is_still_muted() -> None:
    now = datetime.now(timezone.utc)
    competitor = _competitor(CompetitorStatus.muted, muted_until=now + timedelta(days=1))
    assert is_muted(competitor, now) is True


def test_muted_until_past_is_no_longer_muted() -> None:
    now = datetime.now(timezone.utc)
    competitor = _competitor(CompetitorStatus.muted, muted_until=now - timedelta(days=1))
    assert is_muted(competitor, now) is False
