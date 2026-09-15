import asyncio
import uuid

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.extraction import Extraction
from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.snapshot import Snapshot
from app.models.source import Source, SourceType
from app.repositories import competitors as competitors_repo
from app.repositories import extractions as extractions_repo
from app.repositories import findings as findings_repo
from app.schemas.extraction_fields import Changeset, PricingPageFields, SourceConfig, WebsitePageFields
from app.services import findings as findings_service
from app.services.classification import ClassificationOutcome, classify
from app.services.diffing import diff_pricing, diff_website
from app.services.significance import is_significant
from app.tasks.routing import route_finding_task

_EMPTY_CHANGESET = Changeset(fields=[])


@celery_app.task(name="diff_extraction", bind=True, max_retries=3)
def diff_extraction_task(self, extraction_id: str) -> None:
    asyncio.run(_diff_extraction_async(uuid.UUID(extraction_id)))


async def _diff_extraction_async(extraction_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        extraction = await db.get(Extraction, extraction_id)
        if extraction is None:
            return

        snapshot = await db.get(Snapshot, extraction.snapshot_id)
        source = await db.get(Source, snapshot.source_id)
        if source is None:
            return

        workspace_id = extraction.workspace_id
        previous = await extractions_repo.get_latest_successful_for_source(
            db, workspace_id, source.id, exclude_extraction_id=extraction.id
        )

        if previous is None or previous.schema_version != extraction.schema_version:
            # No baseline yet, or the schema shape changed — either way
            # this is a re-baseline, not a field diff (docs/scraping.md:
            # schema version changes are not findings).
            await _write_baseline_finding(db, workspace_id, source, extraction)
            await competitors_repo.activate_if_pending(db, workspace_id, source.competitor_id)
            await db.commit()
            return

        current_fields, previous_fields = _parse_fields(source.type, extraction, previous)
        changeset = (
            diff_pricing(previous_fields, current_fields)
            if source.type == SourceType.pricing_page
            else diff_website(previous_fields, current_fields)
        )
        if changeset is None:
            return

        source_config = SourceConfig.model_validate(source.config)
        if not is_significant(changeset, source_config):
            # Cheapest possible win (docs/llm-usage.md Rule 1): whitespace,
            # reordering, and known-noise churn never reaches the model,
            # and never becomes a finding at all.
            return

        classification = await classify(db, workspace_id, source.url, source.type, changeset)

        if classification.outcome == ClassificationOutcome.success:
            assert classification.result is not None
            change_type = classification.result.change_type
            urgency = classification.result.urgency
            title = classification.result.title
            summary = classification.result.summary
            classification_status = ClassificationStatus.ok
        else:
            # Never drop the finding on a malformed response or a
            # budget-parked call — the diff is durable and real, only the
            # label is missing (docs/rules.md: silence is never success).
            change_type = ChangeType.pricing if source.type == SourceType.pricing_page else ChangeType.other
            urgency = Urgency.low
            title, summary = findings_service.build_title_and_summary(
                change_type, changeset, competitor_name=source.url
            )
            classification_status = (
                ClassificationStatus.pending
                if classification.outcome == ClassificationOutcome.budget_exhausted
                else ClassificationStatus.failed
            )

        dedupe_key = findings_service.compute_dedupe_key(source.competitor_id, change_type, changeset)

        existing = await findings_repo.get_by_dedupe_key(db, workspace_id, dedupe_key)
        if existing is not None:
            # Idempotency: a retried diff of the same real change must not
            # duplicate the finding.
            return

        finding = await findings_repo.create(
            db,
            workspace_id,
            source.competitor_id,
            source.id,
            extraction.snapshot_id,
            change_type,
            urgency,
            title,
            summary,
            changeset.model_dump(mode="json"),
            False,
            dedupe_key,
            classification_status,
        )
        await db.commit()

    route_finding_task.delay(str(finding.id))


async def _write_baseline_finding(db, workspace_id: uuid.UUID, source: Source, extraction: Extraction) -> None:
    change_type = ChangeType.pricing if source.type == SourceType.pricing_page else ChangeType.other
    # Baseline dedupe keys are keyed on the extraction, not the changeset
    # (there is none) — each baseline crawl is its own event, never
    # collapsed with another baseline.
    dedupe_key = f"baseline:{extraction.id}"
    await findings_repo.create(
        db,
        workspace_id,
        source.competitor_id,
        source.id,
        extraction.snapshot_id,
        change_type,
        Urgency.low,
        title=f"Baseline captured for {source.url}",
        summary="Initial crawl — nothing to compare against yet.",
        changeset=_EMPTY_CHANGESET.model_dump(mode="json"),
        is_baseline=True,
        dedupe_key=dedupe_key,
        classification_status=ClassificationStatus.ok,
    )


def _parse_fields(
    source_type: SourceType, extraction: Extraction, previous: Extraction
) -> tuple[PricingPageFields | WebsitePageFields, PricingPageFields | WebsitePageFields]:
    if source_type == SourceType.pricing_page:
        return (
            PricingPageFields.model_validate(extraction.fields),
            PricingPageFields.model_validate(previous.fields),
        )
    return (
        WebsitePageFields.model_validate(extraction.fields),
        WebsitePageFields.model_validate(previous.fields),
    )
