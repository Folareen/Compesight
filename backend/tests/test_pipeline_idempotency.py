import uuid
from unittest.mock import patch

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.extraction import Extraction
from app.models.finding import Finding
from app.models.snapshot import Snapshot
from app.models.source import Source, SourceType
from app.repositories import competitors as competitors_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.tasks.crawling import _crawl_source_async
from app.tasks.diffing import _diff_extraction_async


async def _setup_source(url: str):
    """Task functions under test open their own session via
    async_session_factory and commit — those writes don't roll back with
    the db_session fixture's rollback used elsewhere, so this setup also
    commits through its own fresh session, and every test uses a unique
    clerk id to avoid collisions with rows earlier tests left behind."""
    unique = uuid.uuid4().hex[:8]
    async with async_session_factory() as setup_db:
        user = await users_repo.create(
            setup_db, clerk_user_id=f"crawl-user-{unique}", email=f"crawl-{unique}@example.com", name="C"
        )
        workspace = await workspaces_repo.create_with_owner(
            setup_db, name="Crawl Co", slug=f"crawl-co-{unique}", user_id=user.id
        )
        competitor = await competitors_repo.create(
            setup_db, workspace.id, name="Rival", website_url="https://rival.example"
        )
        source = await sources_repo.create(
            setup_db, workspace.id, competitor.id, SourceType.pricing_page, url, {}, 3600
        )
        await setup_db.commit()
    return workspace, competitor, source


async def _set_url(source_id: uuid.UUID, url: str) -> None:
    async with async_session_factory() as db:
        source = await db.get(Source, source_id)
        source.url = url
        await db.commit()


async def test_repeated_crawl_of_unchanged_content_writes_one_snapshot_per_attempt_but_extracts_once(
    fixture_server: str,
) -> None:
    _, _, source = await _setup_source(f"{fixture_server}/pricing_baseline.html")

    with patch("app.tasks.crawling.diff_extraction_task.delay"):
        await _crawl_source_async(source.id)
        await _crawl_source_async(source.id)

    async with async_session_factory() as fresh_db:
        snapshots = (
            (await fresh_db.execute(select(Snapshot).where(Snapshot.source_id == source.id))).scalars().all()
        )
        extractions = (
            (await fresh_db.execute(select(Extraction).where(Extraction.workspace_id == source.workspace_id)))
            .scalars()
            .all()
        )

    assert len(snapshots) == 2  # every attempt is recorded
    assert len(extractions) == 1  # short-circuit: second crawl's hash matched, no re-extraction


async def test_diffing_the_same_extraction_twice_does_not_duplicate_finding(fixture_server: str) -> None:
    _, _, source = await _setup_source(f"{fixture_server}/pricing_baseline.html")

    with patch("app.tasks.crawling.diff_extraction_task.delay"):
        await _crawl_source_async(source.id)  # baseline extraction, no previous to diff against

    await _set_url(source.id, f"{fixture_server}/pricing_price_change.html")

    with patch("app.tasks.crawling.diff_extraction_task.delay"):
        await _crawl_source_async(source.id)  # real change -> second extraction

    async with async_session_factory() as fresh_db:
        extractions = (
            (await fresh_db.execute(select(Extraction).where(Extraction.workspace_id == source.workspace_id)))
            .scalars()
            .all()
        )
    assert len(extractions) == 2
    latest_extraction = max(extractions, key=lambda e: e.created_at)

    await _diff_extraction_async(latest_extraction.id)
    await _diff_extraction_async(latest_extraction.id)  # re-run: must not duplicate

    async with async_session_factory() as fresh_db:
        findings = (
            (await fresh_db.execute(select(Finding).where(Finding.workspace_id == source.workspace_id)))
            .scalars()
            .all()
        )

    real_changes = [f for f in findings if not f.is_baseline]
    assert len(real_changes) == 1
