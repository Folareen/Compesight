from app.models.finding_feedback import FindingFeedback
from app.models.source import SourceType
from app.schemas.extraction_fields import Changeset

PROMPT_VERSION = "classification_v1"

SYSTEM_PROMPT = """You classify a competitor's detected change into a type and urgency.

change_type: pricing, feature_launch, messaging, hiring, funding, partnership, content, other
urgency:
- high: pricing changed, a competing feature launched, funding or acquisition announced
- medium: notable positioning/messaging shift, significant content or product update
- low: routine content, minor copy, hiring, small cosmetic change

Write a short title (<80 chars) and a one-sentence summary of what changed, grounded only in the
fields given below. Never invent details not present in the changeset."""


def build_user_message(
    competitor_name: str,
    source_type: SourceType,
    changeset: Changeset,
    feedback_examples: list[FindingFeedback],
) -> str:
    lines = [f"Competitor: {competitor_name}", f"Source type: {source_type.value}", "Changed fields:"]
    for change in changeset.fields:
        lines.append(f"- {change.path}: {change.old_value!r} -> {change.new_value!r}")

    if feedback_examples:
        lines.append("\nPast corrections from this workspace (prefer matching their judgment):")
        for fb in feedback_examples:
            correction = fb.corrected_change_type or fb.corrected_urgency
            if correction is None and fb.verdict.value != "noise":
                continue
            lines.append(
                f"- verdict={fb.verdict.value}"
                + (f", corrected_change_type={fb.corrected_change_type.value}" if fb.corrected_change_type else "")
                + (f", corrected_urgency={fb.corrected_urgency.value}" if fb.corrected_urgency else "")
            )

    return "\n".join(lines)
