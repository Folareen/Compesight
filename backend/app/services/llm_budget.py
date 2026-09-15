import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.workspace import Workspace
from app.repositories import llm_usage as llm_usage_repo


class BudgetStatus(str, enum.Enum):
    ok = "ok"
    soft_warn = "soft_warn"
    hard_stop = "hard_stop"


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def check_budget(db: AsyncSession, workspace: Workspace, now: datetime | None = None) -> BudgetStatus:
    """A `llm_budget_cents_monthly` of 0 means unlimited — Phase 9 owns
    plan-bound limits and the UX around them; this only builds the
    mechanism classification and extraction-fallback call before spending."""
    if workspace.llm_budget_cents_monthly <= 0:
        return BudgetStatus.ok

    now = now or datetime.now(timezone.utc)
    spent = await llm_usage_repo.total_cost_cents_since(db, workspace.id, _month_start(now))

    if spent >= workspace.llm_budget_cents_monthly:
        return BudgetStatus.hard_stop
    if spent >= workspace.llm_budget_cents_monthly * settings.llm_budget_soft_warn_ratio:
        return BudgetStatus.soft_warn
    return BudgetStatus.ok
