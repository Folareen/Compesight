import re

from app.schemas.extraction_fields import Changeset, FieldChange, SourceConfig

_NOISE_PATH_PATTERNS = (
    re.compile(r"copyright|\bright(s)?\s+reserved\b|\ball rights\b", re.IGNORECASE),
    re.compile(r"last[\s_-]?updated", re.IGNORECASE),
    re.compile(r"\b(csrf|xsrf)[\s_-]?token\b", re.IGNORECASE),
    re.compile(r"\bsession[\s_-]?id\b", re.IGNORECASE),
)
_NOISE_VALUE_PATTERNS = (
    re.compile(r"[?&](utm_[a-z]+|ref|_ga|_gid|cache[_-]?bust)=", re.IGNORECASE),
    re.compile(r"\bsession[_-]?id=", re.IGNORECASE),
)


def _normalize(value: object) -> object:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return sorted(_normalize(v) for v in value)
    return value


def _is_noise_field(change: FieldChange) -> bool:
    if any(pattern.search(change.path) for pattern in _NOISE_PATH_PATTERNS):
        return True
    return any(pattern.search(str(change.new_value)) for pattern in _NOISE_VALUE_PATTERNS)


def is_significant(changeset: Changeset, source_config: SourceConfig) -> bool:
    """Rules-based, no model call — the cheapest win per docs/llm-usage.md
    Rule 1. Drops whitespace/order-only churn, list-reordering with
    identical members, known noise fields (copyright years, cache-busting
    params, session/CSRF tokens), and fields the source config marks
    `ignore`. Returns True only if at least one field change survives."""
    for change in changeset.fields:
        if change.path in source_config.ignore_fields:
            continue
        if _is_noise_field(change):
            continue
        if _normalize(change.old_value) == _normalize(change.new_value):
            continue
        return True
    return False
