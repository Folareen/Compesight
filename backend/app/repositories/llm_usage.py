import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LlmPurpose, LlmUsage
from app.repositories.scoped import workspace_scoped


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    purpose: LlmPurpose,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_cents: int,
) -> LlmUsage:
    usage = LlmUsage(
        workspace_id=workspace_id,
        purpose=purpose,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_cents=cost_cents,
    )
    db.add(usage)
    await db.flush()
    return usage


async def total_cost_cents_since(db: AsyncSession, workspace_id: uuid.UUID, since: datetime) -> int:
    stmt = workspace_scoped(
        select(func.coalesce(func.sum(LlmUsage.cost_cents), 0)).where(LlmUsage.created_at >= since),
        LlmUsage,
        workspace_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one()
