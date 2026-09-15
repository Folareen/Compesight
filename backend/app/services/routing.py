import uuid

from app.models.competitor import Competitor, CompetitorStatus
from app.models.finding import ChangeType, Urgency
from app.models.routing_rule import RoutingRule

_URGENCY_RANK = {Urgency.low: 0, Urgency.medium: 1, Urgency.high: 2}


def is_muted(competitor: Competitor, now) -> bool:
    if competitor.status == CompetitorStatus.muted:
        return competitor.muted_until is None or competitor.muted_until > now
    return False


def resolve_channels(
    candidates: list[RoutingRule],
    competitor_id: uuid.UUID,
    change_type: ChangeType,
    urgency: Urgency,
) -> list[uuid.UUID]:
    """Most specific match wins (docs/data-model.md): competitor+type,
    then competitor, then workspace+type, then workspace default. Only
    the single most specific matching, enabled rule fires — it does not
    merge channels across specificity levels."""
    rule = _best_match(candidates, competitor_id, change_type)
    if rule is None:
        return []
    if _URGENCY_RANK[urgency] < _URGENCY_RANK[rule.min_urgency]:
        return []
    return list(rule.channels)


def _best_match(
    candidates: list[RoutingRule], competitor_id: uuid.UUID, change_type: ChangeType
) -> RoutingRule | None:
    # A rule scoped to a *different* competitor never matches at all — it
    # is not "less specific", it is irrelevant. Only rules for this
    # competitor or the workspace default (competitor_id is None) compete.
    applicable = [r for r in candidates if r.competitor_id in (None, competitor_id)]

    for competitor_scoped in (True, False):
        for type_scoped in (True, False):
            for rule in applicable:
                rule_is_competitor_scoped = rule.competitor_id == competitor_id
                rule_is_type_scoped = rule.change_type == change_type
                if rule_is_competitor_scoped != competitor_scoped:
                    continue
                if rule_is_type_scoped != type_scoped:
                    continue
                return rule
    return None
