import pytest
from playwright.async_api import Page

from app.schemas.extraction_fields import SourceConfig
from app.services.extraction import ExtractionFailed, extract_pricing_page

_DEFAULT_CONFIG = SourceConfig()


async def test_extract_pricing_page_baseline(fixture_server: str, playwright_page: Page) -> None:
    await playwright_page.goto(f"{fixture_server}/pricing_baseline.html")

    fields = await extract_pricing_page(playwright_page, _DEFAULT_CONFIG)

    assert len(fields.tiers) == 3
    by_name = {t.name: t for t in fields.tiers}
    assert by_name["Basic"].price_minor_units == 1900
    assert by_name["Basic"].currency == "USD"
    assert by_name["Basic"].billing_period == "monthly"
    assert by_name["Pro"].price_minor_units == 4900
    assert by_name["Pro"].highlighted is True
    assert by_name["Basic"].highlighted is False
    assert by_name["Enterprise"].price_minor_units == 19900
    assert by_name["Pro"].features == sorted(by_name["Pro"].features)


async def test_extract_pricing_page_malformed_raises(fixture_server: str, playwright_page: Page) -> None:
    await playwright_page.goto(f"{fixture_server}/pricing_malformed.html")

    with pytest.raises(ExtractionFailed):
        await extract_pricing_page(playwright_page, _DEFAULT_CONFIG)


async def test_extract_pricing_page_price_change(fixture_server: str, playwright_page: Page) -> None:
    await playwright_page.goto(f"{fixture_server}/pricing_price_change.html")

    fields = await extract_pricing_page(playwright_page, _DEFAULT_CONFIG)

    by_name = {t.name: t for t in fields.tiers}
    assert by_name["Pro"].price_minor_units == 5900
