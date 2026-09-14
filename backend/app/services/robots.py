import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx

from app.config import settings


class RobotsDisallowed(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


_cache: dict[str, tuple[urllib.robotparser.RobotFileParser, float]] = {}


async def _get_parser(origin: str) -> urllib.robotparser.RobotFileParser:
    cached = _cache.get(origin)
    if cached is not None:
        parser, cached_at = cached
        if time.monotonic() - cached_at < settings.robots_cache_ttl_seconds:
            return parser

    parser = urllib.robotparser.RobotFileParser()
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            # Unreachable robots.txt is treated as permissive — the site's
            # actual content fetch will surface any real reachability
            # problem as a crawl failure through the normal health path.
            parser.parse([])
            _cache[origin] = (parser, time.monotonic())
            return parser

    if response.status_code >= 400:
        parser.parse([])
    else:
        parser.parse(response.text.splitlines())

    _cache[origin] = (parser, time.monotonic())
    return parser


async def check_allowed(url: str, user_agent: str) -> None:
    """Raise RobotsDisallowed if robots.txt forbids fetching `url` for
    `user_agent`. Never returns a bool a caller could ignore — disallowed
    is a hard stop, not a value to check (docs/scraping.md: no override
    flag, ever)."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parser = await _get_parser(origin)
    if not parser.can_fetch(user_agent, url):
        raise RobotsDisallowed(f"robots.txt disallows fetching {url}")
