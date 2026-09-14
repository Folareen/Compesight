import pytest
from playwright.async_api import Page

from app.schemas.extraction_fields import SourceConfig
from app.services.diffing import diff_pricing
from app.services.extraction import extract_pricing_page

_CONFIG = SourceConfig()


async def _extract(fixture_server: str, page: Page, filename: str):
    await page.goto(f"{fixture_server}/{filename}")
    return await extract_pricing_page(page, _CONFIG)


@pytest.mark.parametrize(
    "fixture_filename",
    [
        "pricing_baseline.html",
        "pricing_whitespace_only.html",
        "pricing_reordered_features.html",
        "pricing_copyright_rollover.html",
    ],
)
async def test_no_finding_for_insignificant_variants(
    fixture_server: str, playwright_page: Page, fixture_filename: str
) -> None:
    previous = await _extract(fixture_server, playwright_page, "pricing_baseline.html")
    current = await _extract(fixture_server, playwright_page, fixture_filename)

    assert diff_pricing(previous, current) is None


async def test_price_change_produces_exactly_one_field_change(
    fixture_server: str, playwright_page: Page
) -> None:
    previous = await _extract(fixture_server, playwright_page, "pricing_baseline.html")
    current = await _extract(fixture_server, playwright_page, "pricing_price_change.html")

    changeset = diff_pricing(previous, current)

    assert changeset is not None
    assert len(changeset.fields) == 1
    change = changeset.fields[0]
    assert change.path == "tiers[pro].price_minor_units"
    assert change.old_value == 4900
    assert change.new_value == 5900


async def test_tier_added_produces_exactly_one_field_change(
    fixture_server: str, playwright_page: Page
) -> None:
    previous = await _extract(fixture_server, playwright_page, "pricing_baseline.html")
    current = await _extract(fixture_server, playwright_page, "pricing_tier_added.html")

    changeset = diff_pricing(previous, current)

    assert changeset is not None
    assert len(changeset.fields) == 1
    change = changeset.fields[0]
    assert change.old_value is None
    assert change.new_value == "Ultimate"


async def test_baseline_vs_self_produces_no_finding(fixture_server: str, playwright_page: Page) -> None:
    previous = await _extract(fixture_server, playwright_page, "pricing_baseline.html")
    current = await _extract(fixture_server, playwright_page, "pricing_baseline.html")

    assert diff_pricing(previous, current) is None


async def test_no_previous_extraction_is_not_diffed(fixture_server: str, playwright_page: Page) -> None:
    current = await _extract(fixture_server, playwright_page, "pricing_baseline.html")
    assert diff_pricing(None, current) is None
