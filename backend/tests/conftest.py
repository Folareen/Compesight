import threading
import uuid
from collections.abc import AsyncGenerator, Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from playwright.async_api import Browser, Page, async_playwright
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "postgresql+asyncpg://compesight:compesight@localhost:5432/compesight_test"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    yield
    command.downgrade(alembic_cfg, "base")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_shared_engine_pool() -> AsyncGenerator[None]:
    """app.db.session.engine is a module-level singleton pooling asyncpg
    connections. Each test runs on its own event loop (pytest-asyncio's
    default function scope); a pooled connection opened on a previous
    test's loop is invalid on this one. Dispose the pool before every test
    that might touch the shared engine (directly, or via task code calling
    async_session_factory) so it reconnects fresh on the current loop."""
    from app.db.session import engine

    await engine.dispose()

    import app.services.rate_limiter as rate_limiter_module
    import app.tasks.scheduling as scheduling_module

    # Don't attempt a graceful aclose() — the client's connection is bound
    # to whatever event loop was current when it was first constructed,
    # which is a previous, now-closed test loop by this point. Just drop
    # the reference so the next test's use constructs a fresh client on
    # its own (current) loop.
    rate_limiter_module._redis = None
    scheduling_module._redis = None

    yield


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture
def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(scope="session")
def fixture_server() -> Iterator[str]:
    """Serves tests/fixtures/html/*.html over plain HTTP on an OS-assigned
    localhost port for the whole test session. Playwright navigates here
    instead of any live site — deterministic, fast, no network access."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURES_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


@pytest_asyncio.fixture
async def playwright_browser() -> AsyncGenerator[Browser]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def playwright_page(playwright_browser: Browser) -> AsyncGenerator[Page]:
    page = await playwright_browser.new_page()
    yield page
    await page.close()
