import asyncio
import uuid

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.extraction import Extraction
from app.models.finding import ChangeType, ClassificationStatus, Urgency
from app.models.snapshot import Snapshot
from app.models.source import Source, SourceType
from app.repositories import extractions as extractions_repo
from app.repositories import findings as findings_repo
from app.schemas.extraction_fields import Changeset, PricingPageFields, WebsitePageFields
from app.services import findings as findings_service
from app.services.diffing import diff_pricing, diff_website

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

        change_type, urgency = findings_service.classify_mechanically(changeset, source.type)
        dedupe_key = findings_service.compute_dedupe_key(source.competitor_id, change_type, changeset)

        existing = await findings_repo.get_by_dedupe_key(db, workspace_id, dedupe_key)
        if existing is not None:
            # Idempotency: a retried diff of the same real change must not
            # duplicate the finding.
            return

        title, summary = findings_service.build_title_and_summary(
            change_type, changeset, competitor_name=source.url
        )
        await findings_repo.create(
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
            ClassificationStatus.ok,
        )
        await db.commit()


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
