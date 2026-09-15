import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ChangeType, Urgency
from app.models.llm_usage import LlmUsage
from app.models.source import SourceType
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.extraction_fields import Changeset, FieldChange
from app.services.classification import ClassificationOutcome, classify

_CHANGESET = Changeset(
    fields=[FieldChange(path="tiers.0.price_minor_units", old_value=1900, new_value=2900)]
)


def _fake_response(text: str, input_tokens: int = 50, output_tokens: int = 20) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


_VALID_JSON = json.dumps(
    {"change_type": "pricing", "urgency": "high", "title": "Price increased", "summary": "Pro tier went up"}
)


async def _workspace(db_session: AsyncSession, slug: str, budget_cents: int = 0):
    user = await users_repo.create(db_session, clerk_user_id=f"clf-{slug}", email=f"{slug}@example.com", name="U")
    workspace = await workspaces_repo.create_with_owner(db_session, name="Co", slug=slug, user_id=user.id)
    workspace.llm_budget_cents_monthly = budget_cents
    await db_session.flush()
    return workspace


async def test_valid_response_classifies_and_writes_usage(db_session: AsyncSession) -> None:
    workspace = await _workspace(db_session, "clf-valid")

    with patch(
        "app.services.classification.get_client",
        return_value=SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=_fake_response(_VALID_JSON)))),
    ):
        result = await classify(db_session, workspace.id, "Rival", SourceType.pricing_page, _CHANGESET)

    assert result.outcome == ClassificationOutcome.success
    assert result.result is not None
    assert result.result.change_type == ChangeType.pricing
    assert result.result.urgency == Urgency.high

    usage_rows = (
        (await db_session.execute(select(LlmUsage).where(LlmUsage.workspace_id == workspace.id))).scalars().all()
    )
    assert len(usage_rows) == 1
    assert usage_rows[0].input_tokens == 50


async def test_malformed_then_valid_succeeds_after_one_retry(db_session: AsyncSession) -> None:
    workspace = await _workspace(db_session, "clf-retry")

    mock_create = AsyncMock(side_effect=[_fake_response("not json"), _fake_response(_VALID_JSON)])
    with patch(
        "app.services.classification.get_client",
        return_value=SimpleNamespace(messages=SimpleNamespace(create=mock_create)),
    ):
        result = await classify(db_session, workspace.id, "Rival", SourceType.pricing_page, _CHANGESET)

    assert result.outcome == ClassificationOutcome.success
    assert mock_create.await_count == 2

    usage_rows = (
        (await db_session.execute(select(LlmUsage).where(LlmUsage.workspace_id == workspace.id))).scalars().all()
    )
    assert len(usage_rows) == 2  # a row for every call actually made, including the failed attempt


async def test_malformed_both_attempts_fails_but_still_tracks_usage(db_session: AsyncSession) -> None:
    workspace = await _workspace(db_session, "clf-fail")

    mock_create = AsyncMock(return_value=_fake_response("still not json"))
    with patch(
        "app.services.classification.get_client",
        return_value=SimpleNamespace(messages=SimpleNamespace(create=mock_create)),
    ):
        result = await classify(db_session, workspace.id, "Rival", SourceType.pricing_page, _CHANGESET)

    assert result.outcome == ClassificationOutcome.failed
    assert result.result is None
    assert mock_create.await_count == 2

    usage_rows = (
        (await db_session.execute(select(LlmUsage).where(LlmUsage.workspace_id == workspace.id))).scalars().all()
    )
    assert len(usage_rows) == 2


async def test_budget_hard_stop_skips_the_call_entirely(db_session: AsyncSession) -> None:
    workspace = await _workspace(db_session, "clf-budget", budget_cents=100)
    from app.models.llm_usage import LlmPurpose
    from app.repositories import llm_usage as llm_usage_repo

    await llm_usage_repo.create(db_session, workspace.id, LlmPurpose.classification, "claude-haiku-4-5", 1, 1, 100)
    await db_session.flush()

    mock_create = AsyncMock()
    with patch(
        "app.services.classification.get_client",
        return_value=SimpleNamespace(messages=SimpleNamespace(create=mock_create)),
    ):
        result = await classify(db_session, workspace.id, "Rival", SourceType.pricing_page, _CHANGESET)

    assert result.outcome == ClassificationOutcome.budget_exhausted
    mock_create.assert_not_awaited()

    usage_rows = (
        (await db_session.execute(select(LlmUsage).where(LlmUsage.workspace_id == workspace.id))).scalars().all()
    )
    assert len(usage_rows) == 1  # only the pre-seeded row — no new call was made
