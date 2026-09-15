from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel

from app.config import settings
from app.models.source import SourceType

_CANDIDATE_PATHS: list[tuple[str, SourceType]] = [
    ("/feed", SourceType.rss),
    ("/rss", SourceType.rss),
    ("/rss.xml", SourceType.rss),
    ("/feed.xml", SourceType.rss),
    ("/blog/rss", SourceType.rss),
    ("/blog/feed", SourceType.rss),
    ("/blog", SourceType.website),
    ("/changelog", SourceType.website),
]

_RSS_CONTENT_TYPES = ("xml", "rss", "atom")


class SourceSuggestion(BaseModel):
    type: SourceType
    url: str


async def discover_sources(website_url: str) -> list[SourceSuggestion]:
    """Probe `website_url`'s domain for common source paths (RSS/blog/
    changelog) plus a GitHub org guessed from the domain name. Plain HTTP
    HEAD/GET only — no Playwright, these are cheap existence checks, not
    crawls, and are never charged against the site's crawl budget.

    Best-effort: an unreachable domain yields an empty list rather than
    raising — discovery failing must never block competitor creation, and
    "found nothing" is a perfectly valid, non-exceptional outcome here
    (unlike a source crawl, there's no health state to protect)."""
    parsed = urlparse(website_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    domain_root = parsed.netloc.removeprefix("www.").split(".")[0]

    suggestions: list[SourceSuggestion] = []
    async with httpx.AsyncClient(
        timeout=settings.source_discovery_timeout_seconds, follow_redirects=True
    ) as client:
        for path, source_type in _CANDIDATE_PATHS:
            candidate_url = urljoin(origin, path)
            if await _probe(client, candidate_url, source_type):
                suggestions.append(SourceSuggestion(type=source_type, url=candidate_url))

        github_url = f"https://github.com/{domain_root}"
        if await _probe_github_org(client, domain_root):
            suggestions.append(SourceSuggestion(type=SourceType.github, url=github_url))

    return suggestions


async def _probe(client: httpx.AsyncClient, url: str, source_type: SourceType) -> bool:
    try:
        response = await client.get(url)
    except httpx.HTTPError:
        return False
    if response.status_code >= 400:
        return False
    if source_type == SourceType.rss:
        content_type = response.headers.get("content-type", "").lower()
        return any(marker in content_type for marker in _RSS_CONTENT_TYPES)
    return True


async def _probe_github_org(client: httpx.AsyncClient, org: str) -> bool:
    try:
        response = await client.get(f"https://api.github.com/orgs/{org}")
    except httpx.HTTPError:
        return False
    return response.status_code == 200
