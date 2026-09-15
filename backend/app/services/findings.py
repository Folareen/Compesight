import hashlib
import uuid

from app.models.finding import ChangeType
from app.schemas.extraction_fields import Changeset


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
    """Deterministic templated text, used when classification fails or is
    budget-parked (LLM prose is the normal path — see
    app/services/classification.py). Must never look degenerate: branches
    on how many fields changed and what kind."""
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
