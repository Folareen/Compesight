import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.extraction import Extraction, ExtractionMethod
from app.models.source import Source, SourceStatus, SourceType
from app.repositories import competitors as competitors_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from app.repositories import workspaces as workspaces_repo
from app.tasks.crawling import _crawl_source_async

_VALID_TIERS_JSON = json.dumps(
    {
        "schema_version": 1,
        "tiers": [
            {
                "name": "Basic",
                "price_minor_units": 1900,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["A"],
                "highlighted": False,
            },
            {
                "name": "Pro",
                "price_minor_units": 4900,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["A", "B"],
                "highlighted": True,
            },
        ],
    }
)


def _fake_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )


async def _setup_source(url: str):
    unique = uuid.uuid4().hex[:8]
    async with async_session_factory() as setup_db:
        user = await users_repo.create(
            setup_db, clerk_user_id=f"fallback-user-{unique}", email=f"fallback-{unique}@example.com", name="U"
        )
        workspace = await workspaces_repo.create_with_owner(
            setup_db, name="Fallback Co", slug=f"fallback-co-{unique}", user_id=user.id
        )
        competitor = await competitors_repo.create(
            setup_db, workspace.id, name="Rival", website_url="https://rival.example"
        )
        source = await sources_repo.create(
            setup_db, workspace.id, competitor.id, SourceType.pricing_page, url, {}, 3600
        )
        await setup_db.commit()
    return workspace, source


async def test_selector_failure_with_llm_success_writes_llm_extraction(fixture_server: str) -> None:
    _, source = await _setup_source(f"{fixture_server}/pricing_malformed.html")

    mock_create = AsyncMock(return_value=_fake_response(_VALID_TIERS_JSON))
    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch(
            "app.services.extraction_llm.get_client",
            return_value=SimpleNamespace(messages=SimpleNamespace(create=mock_create)),
        ),
    ):
        await _crawl_source_async(source.id)

    async with async_session_factory() as fresh_db:
        extractions = (
            (await fresh_db.execute(select(Extraction).where(Extraction.workspace_id == source.workspace_id)))
            .scalars()
            .all()
        )
        refreshed_source = await fresh_db.get(Source, source.id)

    assert len(extractions) == 1
    assert extractions[0].method == ExtractionMethod.llm
    assert refreshed_source.status != SourceStatus.degraded
    assert refreshed_source.extraction_failure_streak == 0


async def test_selector_failure_with_llm_failure_still_marks_degraded(fixture_server: str) -> None:
    _, source = await _setup_source(f"{fixture_server}/pricing_malformed.html")

    mock_create = AsyncMock(return_value=_fake_response("not valid json"))
    with (
        patch("app.tasks.crawling.diff_extraction_task.delay"),
        patch(
            "app.services.extraction_llm.get_client",
            return_value=SimpleNamespace(messages=SimpleNamespace(create=mock_create)),
        ),
    ):
        await _crawl_source_async(source.id)

    async with async_session_factory() as fresh_db:
        extractions = (
            (await fresh_db.execute(select(Extraction).where(Extraction.workspace_id == source.workspace_id)))
            .scalars()
            .all()
        )
        refreshed_source = await fresh_db.get(Source, source.id)

    assert len(extractions) == 0
    assert refreshed_source.status == SourceStatus.degraded
    assert refreshed_source.extraction_failure_streak == 1
