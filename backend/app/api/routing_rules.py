from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.routing_rule import RoutingRule
from app.repositories import competitors as competitors_repo
from app.repositories import notification_channels as channels_repo
from app.repositories import routing_rules as routing_rules_repo
from app.schemas.routing_rule import RoutingRuleListIn, RoutingRuleListOut, RoutingRuleOut

router = APIRouter(prefix="/routing-rules", tags=["routing-rules"])


def _to_rule_out(rule: RoutingRule) -> RoutingRuleOut:
    return RoutingRuleOut(
        id=rule.id,
        competitor_id=rule.competitor_id,
        change_type=rule.change_type,
        min_urgency=rule.min_urgency,
        channels=rule.channels,
        enabled=rule.enabled,
    )


@router.get("", response_model=RoutingRuleListOut)
async def list_routing_rules(
    ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)
) -> RoutingRuleListOut:
    rules = await routing_rules_repo.list_for_workspace(db, ctx.workspace_id)
    return RoutingRuleListOut(rules=[_to_rule_out(r) for r in rules])


@router.put("", response_model=RoutingRuleListOut)
async def replace_routing_rules(
    body: RoutingRuleListIn,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> RoutingRuleListOut:
    # Every competitor_id and channel id in the payload is an untrusted
    # claim until confirmed against this workspace, same as any path id
    # (docs/rules.md rule 1) — check before writing any rule.
    for rule_in in body.rules:
        if rule_in.competitor_id is not None:
            competitor = await competitors_repo.get(db, ctx.workspace_id, rule_in.competitor_id)
            if competitor is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")
        channels = await channels_repo.get_many(db, ctx.workspace_id, rule_in.channels)
        if len(channels) != len(set(rule_in.channels)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")

    rules = await routing_rules_repo.replace_for_workspace(
        db,
        ctx.workspace_id,
        [
            (r.competitor_id, r.change_type, r.min_urgency, r.channels, r.enabled)
            for r in body.rules
        ],
    )
    await db.commit()
    return RoutingRuleListOut(rules=[_to_rule_out(r) for r in rules])
