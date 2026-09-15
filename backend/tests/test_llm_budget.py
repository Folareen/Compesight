from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LlmPurpose
from app.repositories import llm_usage as llm_usage_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.services.llm_budget import BudgetStatus, check_budget

_NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


async def _workspace_with_budget(db_session: AsyncSession, slug: str, budget_cents: int):
    user = await users_repo.create(db_session, clerk_user_id=f"budget-{slug}", email=f"{slug}@example.com", name="U")
    workspace = await workspaces_repo.create_with_owner(db_session, name="Co", slug=slug, user_id=user.id)
    workspace.llm_budget_cents_monthly = budget_cents
    await db_session.flush()
    return workspace


async def test_unlimited_budget_never_stops(db_session: AsyncSession) -> None:
    workspace = await _workspace_with_budget(db_session, "budget-unlimited", 0)
    await llm_usage_repo.create(
        db_session, workspace.id, LlmPurpose.classification, "claude-haiku-4-5", 1_000_000, 1_000_000, 999_999
    )
    await db_session.flush()

    status = await check_budget(db_session, workspace, now=_NOW)
    assert status == BudgetStatus.ok


async def test_spend_below_soft_warn_threshold_is_ok(db_session: AsyncSession) -> None:
    workspace = await _workspace_with_budget(db_session, "budget-ok", 1000)
    await llm_usage_repo.create(
        db_session, workspace.id, LlmPurpose.classification, "claude-haiku-4-5", 100, 100, 700
    )
    await db_session.flush()

    status = await check_budget(db_session, workspace, now=_NOW)
    assert status == BudgetStatus.ok


async def test_spend_at_80_percent_is_soft_warn(db_session: AsyncSession) -> None:
    workspace = await _workspace_with_budget(db_session, "budget-warn", 1000)
    await llm_usage_repo.create(
        db_session, workspace.id, LlmPurpose.classification, "claude-haiku-4-5", 100, 100, 800
    )
    await db_session.flush()

    status = await check_budget(db_session, workspace, now=_NOW)
    assert status == BudgetStatus.soft_warn


async def test_spend_at_100_percent_is_hard_stop(db_session: AsyncSession) -> None:
    workspace = await _workspace_with_budget(db_session, "budget-stop", 1000)
    await llm_usage_repo.create(
        db_session, workspace.id, LlmPurpose.classification, "claude-haiku-4-5", 100, 100, 1000
    )
    await db_session.flush()

    status = await check_budget(db_session, workspace, now=_NOW)
    assert status == BudgetStatus.hard_stop


async def test_spend_from_a_previous_month_does_not_count(db_session: AsyncSession) -> None:
    workspace = await _workspace_with_budget(db_session, "budget-rollover", 1000)
    usage = await llm_usage_repo.create(
        db_session, workspace.id, LlmPurpose.classification, "claude-haiku-4-5", 100, 100, 1000
    )
    usage.created_at = datetime(2026, 8, 15, tzinfo=timezone.utc)
    await db_session.flush()

    status = await check_budget(db_session, workspace, now=_NOW)
    assert status == BudgetStatus.ok
