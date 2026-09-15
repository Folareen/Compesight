import uuid
from unittest.mock import AsyncMock, patch

from app.db.session import async_session_factory
from app.models.competitor import CompetitorStatus
from app.models.source import Source, SourceStatus, SourceType
from app.repositories import competitors as competitors_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.tasks.crawling import _crawl_source_async
from app.tasks.diffing import _diff_extraction_async


async def _setup_source(url: str):
    """Mirrors tests/test_pipeline_idempotency.py's helper: task functions
    under test open their own session and commit, so setup commits through
    its own fresh session rather than the rolled-back db_session fixture."""
    unique = uuid.uuid4().hex[:8]
    async with async_session_factory() as setup_db:
        user = await users_repo.create(
            setup_db, clerk_user_id=f"health-user-{unique}", email=f"health-{unique}@example.com", name="H"
        )
        workspace = await workspaces_repo.create_with_owner(
            setup_db, name="Health Co", slug=f"health-co-{unique}", user_id=user.id
        )
        competitor = await competitors_repo.create(
            setup_db, workspace.id, name="Rival", website_url="https://rival.example"
        )
        source = await sources_repo.create(
            setup_db, workspace.id, competitor.id, SourceType.pricing_page, url, {}, 3600
        )
        await setup_db.commit()
    return workspace, competitor, source


async def _get_source(source_id: uuid.UUID) -> Source:
    async with async_session_factory() as db:
        return await db.get(Source, source_id)


async def _set_url(source_id: uuid.UUID, url: str) -> None:
    async with async_session_factory() as db:
        source = await db.get(Source, source_id)
        source.url = url
        await db.commit()


async def test_extraction_failure_increments_streak_and_degrades(fixture_server: str) -> None:
    _, _, source = await _setup_source(f"{fixture_server}/pricing_malformed.html")

    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch("app.tasks.crawling.extract_with_llm", AsyncMock(return_value=None)),
    ):
        await _crawl_source_async(source.id)

    refreshed = await _get_source(source.id)
    assert refreshed.status == SourceStatus.degraded
    assert refreshed.extraction_failure_streak == 1


async def test_extraction_failure_streak_accumulates_across_crawls(fixture_server: str) -> None:
    """Each crawl must fetch genuinely different content — the content_hash
    short-circuit (docs/scraping.md) skips re-extraction entirely when a
    crawl's hash matches the last snapshot, so three crawls of the *same*
    malformed page would only ever extract (and fail) once."""
    _, _, source = await _setup_source(f"{fixture_server}/pricing_malformed.html")

    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch("app.tasks.crawling.extract_with_llm", AsyncMock(return_value=None)),
    ):
        await _crawl_source_async(source.id)

    await _set_url(source.id, f"{fixture_server}/pricing_malformed_v2.html")
    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch("app.tasks.crawling.extract_with_llm", AsyncMock(return_value=None)),
    ):
        await _crawl_source_async(source.id)

    await _set_url(source.id, f"{fixture_server}/pricing_malformed_v3.html")
    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch("app.tasks.crawling.extract_with_llm", AsyncMock(return_value=None)),
    ):
        await _crawl_source_async(source.id)

    refreshed = await _get_source(source.id)
    assert refreshed.extraction_failure_streak == 3


async def test_successful_extraction_resets_failure_streak(fixture_server: str) -> None:
    _, _, source = await _setup_source(f"{fixture_server}/pricing_malformed.html")

    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch("app.tasks.crawling.extract_with_llm", AsyncMock(return_value=None)),
    ):
        await _crawl_source_async(source.id)

    async with async_session_factory() as db:
        db_source = await db.get(Source, source.id)
        db_source.url = f"{fixture_server}/pricing_baseline.html"
        await db.commit()

    with patch("app.tasks.crawling.diff_extraction_task.delay"):
        await _crawl_source_async(source.id)

    refreshed = await _get_source(source.id)
    assert refreshed.extraction_failure_streak == 0


async def test_baseline_crawl_activates_pending_competitor(fixture_server: str) -> None:
    workspace, competitor, source = await _setup_source(f"{fixture_server}/pricing_baseline.html")
    assert competitor.status == CompetitorStatus.pending

    with patch("app.tasks.crawling.diff_extraction_task.delay") as mocked_delay:
        await _crawl_source_async(source.id)
        extraction_id = uuid.UUID(mocked_delay.call_args[0][0])

    await _diff_extraction_async(extraction_id)

    async with async_session_factory() as db:
        refreshed_competitor = await competitors_repo.get(db, workspace.id, competitor.id)

    assert refreshed_competitor.status == CompetitorStatus.active


async def test_activation_never_overrides_muted_competitor(fixture_server: str) -> None:
    workspace, competitor, source = await _setup_source(f"{fixture_server}/pricing_baseline.html")

    async with async_session_factory() as db:
        await competitors_repo.update(db, workspace.id, competitor.id, name=None, status=CompetitorStatus.muted)
        await db.commit()

    with patch("app.tasks.crawling.diff_extraction_task.delay") as mocked_delay:
        await _crawl_source_async(source.id)
        extraction_id = uuid.UUID(mocked_delay.call_args[0][0])

    await _diff_extraction_async(extraction_id)

    async with async_session_factory() as db:
        refreshed_competitor = await competitors_repo.get(db, workspace.id, competitor.id)

    assert refreshed_competitor.status == CompetitorStatus.muted
