import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ChangeType, Urgency
from app.models.finding_feedback import FeedbackVerdict, FindingFeedback
from app.repositories.scoped import workspace_scoped


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    finding_id: uuid.UUID,
    user_id: uuid.UUID,
    verdict: FeedbackVerdict,
    corrected_change_type: ChangeType | None,
    corrected_urgency: Urgency | None,
) -> FindingFeedback:
    feedback = FindingFeedback(
        workspace_id=workspace_id,
        finding_id=finding_id,
        user_id=user_id,
        verdict=verdict,
        corrected_change_type=corrected_change_type,
        corrected_urgency=corrected_urgency,
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def recent_for_prompt(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    limit: int = 5,
) -> list[FindingFeedback]:
    """Most recent corrections for this workspace, for the classification
    prompt's few-shot examples (docs/llm-usage.md: "Corrections are the
    tuning mechanism"). Capped so the prompt doesn't grow without bound."""
    stmt = workspace_scoped(
        select(FindingFeedback).order_by(FindingFeedback.created_at.desc()).limit(limit),
        FindingFeedback,
        workspace_id,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
