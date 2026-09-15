from app.schemas.extraction_fields import Changeset, FieldChange, SourceConfig

_DEFAULT_CONFIG = SourceConfig()


def _changeset(*changes: FieldChange) -> Changeset:
    return Changeset(fields=list(changes))


def test_whitespace_only_change_is_not_significant() -> None:
    from app.services.significance import is_significant

    changeset = _changeset(FieldChange(path="tiers.0.name", old_value="Pro  Plan", new_value="Pro Plan"))
    assert is_significant(changeset, _DEFAULT_CONFIG) is False


def test_reordered_list_with_identical_members_is_not_significant() -> None:
    from app.services.significance import is_significant

    changeset = _changeset(
        FieldChange(
            path="tiers.0.features", old_value=["A", "B", "C"], new_value=["C", "A", "B"]
        )
    )
    assert is_significant(changeset, _DEFAULT_CONFIG) is False


def test_copyright_year_change_is_not_significant() -> None:
    from app.services.significance import is_significant

    changeset = _changeset(FieldChange(path="footer.copyright", old_value="2025", new_value="2026"))
    assert is_significant(changeset, _DEFAULT_CONFIG) is False


def test_session_id_and_cache_bust_params_are_not_significant() -> None:
    from app.services.significance import is_significant

    changeset = _changeset(
        FieldChange(path="body_digest", old_value="?session_id=abc123", new_value="?session_id=def456")
    )
    assert is_significant(changeset, _DEFAULT_CONFIG) is False


def test_field_marked_ignore_in_source_config_is_not_significant() -> None:
    from app.services.significance import is_significant

    config = SourceConfig(ignore_fields=["tiers.0.name"])
    changeset = _changeset(FieldChange(path="tiers.0.name", old_value="Starter", new_value="Basic"))
    assert is_significant(changeset, config) is False


def test_real_price_change_is_significant() -> None:
    from app.services.significance import is_significant

    changeset = _changeset(
        FieldChange(path="tiers.0.price_minor_units", old_value=1900, new_value=2900)
    )
    assert is_significant(changeset, _DEFAULT_CONFIG) is True


def test_one_significant_field_among_noise_is_still_significant() -> None:
    from app.services.significance import is_significant

    changeset = _changeset(
        FieldChange(path="footer.copyright", old_value="2025", new_value="2026"),
        FieldChange(path="tiers.0.name", old_value="Starter", new_value="Basic"),
    )
    assert is_significant(changeset, _DEFAULT_CONFIG) is True
