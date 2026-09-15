import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.repositories import digests as digests_repo
from app.repositories import findings as findings_repo

_DIGEST_PERIOD = timedelta(days=7)


async def assemble_digest(db: AsyncSession, workspace_id: uuid.UUID, now: datetime) -> tuple[datetime, list[Finding]]:
    """Findings for the workspace's next digest period.

    Continues from the last digest's `period_end` so consecutive weekly
    runs never overlap or skip a window; a workspace with no prior digest
    starts one period back from `now`. Idempotent: re-running for a period
    that already has a `digest` row with `sent_at` set should not be acted
    on by the caller (app.tasks.digest checks that before sending).
    """
    latest = await digests_repo.get_latest(db, workspace_id)
    period_start = latest.period_end if latest is not None else now - _DIGEST_PERIOD
    findings = await findings_repo.list_non_baseline_between(db, workspace_id, period_start, now)
    return period_start, findings
