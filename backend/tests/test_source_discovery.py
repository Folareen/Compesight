import httpx
import pytest

from app.models.source import SourceType
from app.services import source_discovery


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host != "rival.example" and request.url.host != "api.github.com":
        return httpx.Response(404)
    if request.url.path == "/feed":
        return httpx.Response(200, headers={"content-type": "application/rss+xml"}, text="<rss/>")
    if request.url.path == "/blog":
        return httpx.Response(200, text="<html>blog</html>")
    if request.url.path == "/orgs/rival":
        return httpx.Response(200, json={"login": "rival"})
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def _mock_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discovery must never hit the real network in tests — see
    docs/rules.md testing rules. Routes every candidate path through a
    fixed in-memory handler instead of a live site or the real GitHub API."""
    real_client = httpx.AsyncClient

    def _mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(_handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(source_discovery.httpx, "AsyncClient", _mocked_client)


async def test_discovers_rss_feed_and_blog() -> None:
    suggestions = await source_discovery.discover_sources("https://rival.example")

    urls_by_type = {s.type: s.url for s in suggestions}
    assert urls_by_type[SourceType.rss] == "https://rival.example/feed"
    assert urls_by_type[SourceType.website] == "https://rival.example/blog"


async def test_discovers_github_org_from_domain() -> None:
    suggestions = await source_discovery.discover_sources("https://rival.example")

    github = next(s for s in suggestions if s.type == SourceType.github)
    assert github.url == "https://github.com/rival"


async def test_no_suggestions_for_a_domain_with_nothing_found() -> None:
    suggestions = await source_discovery.discover_sources("https://quiet.example")
    assert suggestions == []
