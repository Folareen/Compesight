import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ChangeType, Urgency
from app.models.routing_rule import RoutingRule
from app.repositories.scoped import workspace_scoped


async def list_for_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> list[RoutingRule]:
    stmt = workspace_scoped(select(RoutingRule), RoutingRule, workspace_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_candidates_for_competitor(
    db: AsyncSession, workspace_id: uuid.UUID, competitor_id: uuid.UUID
) -> list[RoutingRule]:
    """Every enabled rule that could match this competitor: scoped to it
    specifically, or the workspace default (`competitor_id IS NULL`).
    Specificity resolution (app.services.routing) picks the winner from
    this candidate set."""
    stmt = workspace_scoped(
        select(RoutingRule).where(
            RoutingRule.enabled.is_(True),
            (RoutingRule.competitor_id == competitor_id) | (RoutingRule.competitor_id.is_(None)),
        ),
        RoutingRule,
        workspace_id,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def replace_for_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    rules: list[
        tuple[uuid.UUID | None, ChangeType | None, Urgency, list[uuid.UUID], bool]
    ],
) -> list[RoutingRule]:
    """The routing-rule set is edited as a whole (PUT /api/routing-rules,
    per docs/api-conventions.md) rather than individual rows, so this
    replaces every rule for the workspace in one transaction."""
    existing = await list_for_workspace(db, workspace_id)
    for rule in existing:
        await db.delete(rule)
    await db.flush()

    created = []
    for competitor_id, change_type, min_urgency, channels, enabled in rules:
        rule = RoutingRule(
            workspace_id=workspace_id,
            competitor_id=competitor_id,
            change_type=change_type,
            min_urgency=min_urgency,
            channels=channels,
            enabled=enabled,
        )
        db.add(rule)
        created.append(rule)
    await db.flush()
    return created
