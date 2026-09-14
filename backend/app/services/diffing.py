from app.schemas.extraction_fields import Changeset, FieldChange, PricingPageFields, WebsitePageFields

_WEBSITE_SIMILARITY_THRESHOLD = 0.97
_SHINGLE_SIZE = 3


def _shingles(text: str) -> set[str]:
    words = text.split()
    if len(words) < _SHINGLE_SIZE:
        return {text}
    return {" ".join(words[i : i + _SHINGLE_SIZE]) for i in range(len(words) - _SHINGLE_SIZE + 1)}


def _jaccard_similarity(a: str, b: str) -> float:
    shingles_a, shingles_b = _shingles(a), _shingles(b)
    if not shingles_a and not shingles_b:
        return 1.0
    intersection = len(shingles_a & shingles_b)
    union = len(shingles_a | shingles_b)
    return intersection / union if union else 1.0


def diff_pricing(previous: PricingPageFields | None, current: PricingPageFields) -> Changeset | None:
    """Compares tier-by-tier, matched by normalized (lowercased, trimmed)
    name. A renamed tier reads as one removed + one added — correct and
    honest, not a bug to special-case away. Returns None when nothing
    survived normalization: pricing fields were already normalized at
    extraction time (whitespace collapsed, features sorted), so any
    surviving FieldChange here is a real change, never noise."""
    if previous is None:
        return None

    previous_by_name = {t.name.strip().lower(): t for t in previous.tiers}
    current_by_name = {t.name.strip().lower(): t for t in current.tiers}

    changes: list[FieldChange] = []

    for name, prev_tier in previous_by_name.items():
        if name not in current_by_name:
            changes.append(FieldChange(path=f"tiers[{name}]", old_value=prev_tier.name, new_value=None))

    for name, curr_tier in current_by_name.items():
        if name not in previous_by_name:
            changes.append(FieldChange(path=f"tiers[{name}]", old_value=None, new_value=curr_tier.name))
            continue

        prev_tier = previous_by_name[name]
        if prev_tier.price_minor_units != curr_tier.price_minor_units:
            changes.append(
                FieldChange(
                    path=f"tiers[{name}].price_minor_units",
                    old_value=prev_tier.price_minor_units,
                    new_value=curr_tier.price_minor_units,
                )
            )
        if prev_tier.currency != curr_tier.currency:
            changes.append(
                FieldChange(
                    path=f"tiers[{name}].currency", old_value=prev_tier.currency, new_value=curr_tier.currency
                )
            )
        if prev_tier.billing_period != curr_tier.billing_period:
            changes.append(
                FieldChange(
                    path=f"tiers[{name}].billing_period",
                    old_value=prev_tier.billing_period,
                    new_value=curr_tier.billing_period,
                )
            )
        if prev_tier.features != curr_tier.features:
            changes.append(
                FieldChange(
                    path=f"tiers[{name}].features", old_value=prev_tier.features, new_value=curr_tier.features
                )
            )
        if prev_tier.highlighted != curr_tier.highlighted:
            changes.append(
                FieldChange(
                    path=f"tiers[{name}].highlighted",
                    old_value=prev_tier.highlighted,
                    new_value=curr_tier.highlighted,
                )
            )

    if not changes:
        return None
    return Changeset(fields=changes)


def diff_website(previous: WebsitePageFields | None, current: WebsitePageFields) -> Changeset | None:
    """Title changes exactly (a title is a deliberate choice, not prose
    that drifts). Body digest changes below a similarity threshold are
    treated as insignificant — `website` extraction has no structured
    schema to normalize noise out of the way pricing does, so this
    threshold IS the significance filter for this source type."""
    if previous is None:
        return None

    changes: list[FieldChange] = []
    if previous.title != current.title:
        changes.append(FieldChange(path="title", old_value=previous.title, new_value=current.title))

    similarity = _jaccard_similarity(previous.body_digest, current.body_digest)
    if similarity < _WEBSITE_SIMILARITY_THRESHOLD:
        changes.append(
            FieldChange(path="body_digest", old_value=previous.body_digest, new_value=current.body_digest)
        )

    if not changes:
        return None
    return Changeset(fields=changes)
