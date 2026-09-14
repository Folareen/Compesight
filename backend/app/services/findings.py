import hashlib
import uuid

from app.models.finding import ChangeType, Urgency
from app.models.source import SourceType
from app.schemas.extraction_fields import Changeset


def classify_mechanically(changeset: Changeset, source_type: SourceType) -> tuple[ChangeType, Urgency]:
    """Deterministic, non-LLM classification — Phase 3 replaces this with a
    model call. Price-figure changes on a pricing page are the highest
    signal this phase can produce mechanically; everything else is
    downgraded but never miscategorized as pricing."""
    if source_type == SourceType.pricing_page:
        price_changed = any(
            "price_minor_units" in change.path or "currency" in change.path for change in changeset.fields
        )
        return ChangeType.pricing, (Urgency.medium if price_changed else Urgency.low)
    return ChangeType.other, Urgency.low


def compute_dedupe_key(competitor_id: uuid.UUID, change_type: ChangeType, changeset: Changeset) -> str:
    """Stable across re-runs of the same real change, computed the same
    way Phase 4's cross-source dedup will need it — no backfill required
    when that lands."""
    stable_fields = sorted((c.path, str(c.new_value)) for c in changeset.fields)
    raw = f"{competitor_id}|{change_type.value}|{stable_fields}"
    return hashlib.sha256(raw.encode()).hexdigest()


def build_title_and_summary(
    change_type: ChangeType, changeset: Changeset, competitor_name: str
) -> tuple[str, str]:
    """Deterministic templated text — a placeholder for Phase 3's LLM
    prose, not itself a classification step. Must never look degenerate:
    branches on how many fields changed and what kind."""
    if change_type == ChangeType.pricing:
        title = f"Pricing changed on {competitor_name}"
    else:
        title = f"{competitor_name} page changed"

    if len(changeset.fields) == 1:
        change = changeset.fields[0]
        summary = f"{change.path}: {change.old_value!r} → {change.new_value!r}"
    else:
        summary = f"{len(changeset.fields)} fields changed: " + ", ".join(c.path for c in changeset.fields)

    return title, summary
