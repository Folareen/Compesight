import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, Playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import settings
from app.models.source import Source
from app.services.crawl_outcome import CrawlOutcome
from app.services.rate_limiter import acquire_host_slot
from app.services.robots import RobotsDisallowed, check_allowed

_BLOCKED_RESOURCE_TYPES = {"image", "font", "media"}

_NOISE_PATTERNS = [
    re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE),
]
_QUERY_NOISE_PARAMS = re.compile(
    r"([?&])(session|sid|csrf|token|_ga|utm_[a-z]+|cache_?bust|v|t|ts)=[^&\"'\s]*", re.IGNORECASE
)
_WHITESPACE = re.compile(r"\s+")


def _normalize_for_hash(html: str) -> str:
    """Strip known noise sources before hashing so `content_hash` is stable
    across identical-content fetches (docs/scraping.md). This does one
    documented job — normalization for hashing — not general HTML cleanup."""
    normalized = html
    for pattern in _NOISE_PATTERNS:
        normalized = pattern.sub("", normalized)
    normalized = _QUERY_NOISE_PARAMS.sub("", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    return normalized


async def _block_heavy_resources(page: Page) -> None:
    async def handler(route):
        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", handler)


@dataclass
class CrawlSession:
    """Bundles a successful crawl's outcome with the still-open Playwright
    handles, so the caller can run extraction against the live `page`
    before closing everything via `close()`. Never leave one of these open
    past the task that requested it."""

    outcome: CrawlOutcome
    page: Page
    _browser: Browser
    _playwright: Playwright

    async def close(self) -> None:
        await self._browser.close()
        await self._playwright.stop()


async def crawl_source(source: Source) -> CrawlOutcome | CrawlSession:
    """Fetch `source.url` with Playwright, honoring robots.txt and per-host
    rate limiting. Never raises for an ordinary crawl failure (timeout,
    non-2xx, network error) — those come back as a bare CrawlOutcome with
    `error` set, because crawl failure is expected, not exceptional.
    Raises RobotsDisallowed so the caller can distinguish "blocked" from
    "failing" — losing that distinction would misclassify a deliberate
    site policy as a retryable glitch.

    On success, returns a CrawlSession — outcome plus the live Page — so
    the caller can run extraction against the real DOM before closing it;
    the caller MUST call `.close()` on it exactly once. On failure, returns
    a bare CrawlOutcome with nothing left open.
    """
    await check_allowed(source.url, settings.crawler_user_agent)

    host = urlparse(source.url).netloc
    await acquire_host_slot(host, settings.crawl_min_host_interval_seconds)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page(user_agent=settings.crawler_user_agent)
    await _block_heavy_resources(page)

    try:
        response = await page.goto(
            source.url, wait_until="networkidle", timeout=settings.crawl_timeout_ms
        )
    except PlaywrightTimeoutError:
        await browser.close()
        await playwright.stop()
        return CrawlOutcome(
            fetched_at=datetime.now(timezone.utc),
            content_hash=None,
            raw_payload=None,
            http_status=None,
            error="timeout",
        )
    except PlaywrightError as exc:
        await browser.close()
        await playwright.stop()
        return CrawlOutcome(
            fetched_at=datetime.now(timezone.utc),
            content_hash=None,
            raw_payload=None,
            http_status=None,
            error=str(exc)[:500],
        )

    http_status = response.status if response is not None else None
    content = await page.content()
    content_hash = hashlib.sha256(_normalize_for_hash(content).encode()).hexdigest()

    outcome = CrawlOutcome(
        fetched_at=datetime.now(timezone.utc),
        content_hash=content_hash,
        raw_payload=content,
        http_status=http_status,
        error=None if http_status is not None and http_status < 400 else f"http {http_status}",
    )

    if outcome.error is not None:
        await browser.close()
        await playwright.stop()
        return outcome

    return CrawlSession(outcome=outcome, page=page, _browser=browser, _playwright=playwright)
