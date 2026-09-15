import asyncio
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.extraction import ExtractionMethod
from app.models.source import Source, SourceStatus, SourceType
from app.repositories import extractions as extractions_repo
from app.repositories import snapshots as snapshots_repo
from app.repositories import sources as sources_repo
from app.schemas.extraction_fields import SourceConfig
from app.services.backoff import backoff_with_jitter
from app.services.crawler import CrawlSession, crawl_source
from app.services.extraction import ExtractionFailed, extract_pricing_page, extract_website_page
from app.services.extraction_llm import extract_with_llm
from app.services.robots import RobotsDisallowed
from app.services.source_health import next_health_state
from app.tasks.diffing import diff_extraction_task


@celery_app.task(name="crawl_source", bind=True, max_retries=5)
def crawl_source_task(self, source_id: str) -> None:
    """Fetch a source, then — while the Playwright page is still open —
    extract it in the same task. Crawl and extract are normally separate
    pipeline stages, but extraction runs against the live `Page` (no
    stored-HTML re-parse), and a live Page can't be handed between queued
    Celery tasks — so this task owns both stages for exactly this seam.
    Diffing stays a separate task (it needs no live page).

    Tasks take ids, not objects: the Source row is always loaded fresh.
    """
    retry_after = asyncio.run(_crawl_source_async(uuid.UUID(source_id)))
    if retry_after is not None:
        raise self.retry(countdown=retry_after)


async def _crawl_source_async(source_id: uuid.UUID) -> float | None:
    """Returns a retry countdown in seconds if the caller should retry,
    else None. Kept as a plain return value (rather than calling
    self.retry from inside the coroutine) so this function stays testable
    without a bound Celery task object."""
    async with async_session_factory() as db:
        source = await db.get(Source, source_id)
        if source is None:
            return None

        now = datetime.now(timezone.utc)

        try:
            result = await crawl_source(source)
        except RobotsDisallowed as exc:
            await sources_repo.update_health(
                db,
                source.workspace_id,
                source.id,
                status=SourceStatus.blocked,
                last_attempt_at=now,
                last_success_at=None,
                consecutive_failures=source.consecutive_failures,
                blocked_reason=exc.reason,
            )
            await db.commit()
            return None

        outcome = result.outcome if isinstance(result, CrawlSession) else result

        new_status, new_failures, blocked_reason = next_health_state(
            source.status, source.consecutive_failures, outcome
        )
        await sources_repo.update_health(
            db,
            source.workspace_id,
            source.id,
            status=new_status,
            last_attempt_at=now,
            last_success_at=now if outcome.error is None else None,
            consecutive_failures=new_failures,
            blocked_reason=blocked_reason if new_status == SourceStatus.blocked else source.blocked_reason,
        )
        await db.commit()

        if outcome.error is not None:
            # Ordinary crawl failure — expected, retried with backoff.
            # `blocked` transitions are terminal and never retried.
            if new_status == SourceStatus.blocked:
                return None
            return backoff_with_jitter(new_failures)

        assert isinstance(result, CrawlSession)

        # Snapshot is always written, even when content is unchanged —
        # it's the audit trail for every attempt, not just changed ones.
        previous_snapshot = await snapshots_repo.get_latest(db, source.workspace_id, source.id)
        snapshot = await snapshots_repo.create(
            db,
            source.workspace_id,
            source.id,
            outcome.fetched_at,
            outcome.content_hash,
            outcome.raw_payload,
            outcome.http_status,
            outcome.error,
        )
        await db.commit()

        content_unchanged = (
            previous_snapshot is not None
            and previous_snapshot.content_hash == outcome.content_hash
            and previous_snapshot.error is None
        )
        if content_unchanged:
            await result.close()
            return None

        extraction_method = ExtractionMethod.selector
        try:
            source_config = SourceConfig.model_validate(source.config)
            if source.type == SourceType.pricing_page:
                fields = await extract_pricing_page(result.page, source_config)
            else:
                fields = await extract_website_page(result.page, source_config)
        except ExtractionFailed:
            # Selectors couldn't find what they expect — try the LLM
            # fallback (docs/llm-usage.md) against the raw page text before
            # giving up. `method` on the extraction row is what drives the
            # extraction-drift health signal, so it must reflect whichever
            # path actually produced the fields.
            page_text = " ".join((await result.page.locator("body").inner_text()).split())
            llm_fields = await extract_with_llm(db, source.workspace_id, source.type, page_text)
            if llm_fields is None:
                # Extraction-drift signal (docs/scraping.md): fetches
                # succeed but neither selectors nor the LLM fallback can
                # find what they expect. Tracked as its own streak,
                # separate from consecutive_failures (an ordinary fetch
                # failure) — repeated failures here mean the page was
                # redesigned, not that the site is unreachable.
                streak = source.extraction_failure_streak + 1
                await sources_repo.update_health(
                    db,
                    source.workspace_id,
                    source.id,
                    status=SourceStatus.degraded,
                    last_attempt_at=now,
                    last_success_at=now,
                    consecutive_failures=source.consecutive_failures,
                    blocked_reason=None,
                    extraction_failure_streak=streak,
                )
                await db.commit()
                await result.close()
                return None
            fields = llm_fields
            extraction_method = ExtractionMethod.llm

        extraction = await extractions_repo.create(
            db,
            source.workspace_id,
            snapshot.id,
            fields.schema_version,
            fields.model_dump(mode="json"),
            extraction_method,
            confidence=1.0 if extraction_method == ExtractionMethod.selector else 0.7,
        )
        if source.extraction_failure_streak != 0:
            await sources_repo.update_health(
                db,
                source.workspace_id,
                source.id,
                status=source.status,
                last_attempt_at=now,
                last_success_at=now,
                consecutive_failures=source.consecutive_failures,
                blocked_reason=source.blocked_reason,
                extraction_failure_streak=0,
            )
        await db.commit()
        await result.close()

        diff_extraction_task.delay(str(extraction.id))
        return None
