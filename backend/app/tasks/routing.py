import asyncio
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.competitor import Competitor
from app.models.finding import Finding
from app.repositories import alerts as alerts_repo
from app.repositories import routing_rules as routing_rules_repo
from app.services.routing import is_muted, resolve_channels
from app.tasks.delivery import deliver_alert_task


@celery_app.task(name="route_finding")
def route_finding_task(finding_id: str) -> None:
    asyncio.run(_route_finding_async(uuid.UUID(finding_id)))


async def _route_finding_async(finding_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        finding = await db.get(Finding, finding_id)
        if finding is None or finding.is_baseline:
            # Baseline findings populate the timeline and battlecard but
            # never alert (docs/architecture.md pipeline stages 5-7).
            return

        competitor = await db.get(Competitor, finding.competitor_id)
        if competitor is None:
            return

        now = datetime.now(timezone.utc)
        if is_muted(competitor, now):
            return

        candidates = await routing_rules_repo.list_candidates_for_competitor(
            db, finding.workspace_id, finding.competitor_id
        )
        channel_ids = resolve_channels(candidates, finding.competitor_id, finding.change_type, finding.urgency)
        if not channel_ids:
            return

        alert_ids = []
        for channel_id in channel_ids:
            alert = await alerts_repo.create_if_absent(db, finding.workspace_id, finding.id, channel_id)
            if alert is not None:
                alert_ids.append(alert.id)
        await db.commit()

    for alert_id in alert_ids:
        deliver_alert_task.delay(str(alert_id))
