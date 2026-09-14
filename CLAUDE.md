# Compesight

Competitor monitoring web app. Crawls competitors' sites and public presence, detects changes, classifies them with an LLM, surfaces them as alerts and a per-competitor battlecard.

- **What we're building:** [spec.md](spec.md)
- **How to build it:** [docs/](docs/) — start at [docs/README.md](docs/README.md)

## Before writing code

**Read [docs/rules.md](docs/rules.md)** — universal, short, non-negotiable. Then the rules for the side you're touching: [docs/backend-rules.md](docs/backend-rules.md) or [docs/frontend-rules.md](docs/frontend-rules.md).

The three that cause real damage:
1. Every workspace-scoped query filters on `workspace_id`, derived from the session — never from the request.
2. Never log secrets, scraped credentials, or session tokens.
3. Respect robots.txt and rate limits. A banned crawler breaks the product for every customer at once.

Then the doc for the area you're touching — [docs/README.md](docs/README.md) has the table.

## Stack

- `backend/` — FastAPI, Python 3.12+, managed with `uv`. Postgres, Celery + Redis, Playwright.
- `frontend/` — Next.js 16, React 19, Tailwind v4.
- Clerk for identity; we own workspaces and all authorization.

**Next.js 16 is newer than most training data.** Middleware is now Proxy (`proxy.ts`), `cookies()`/`headers()` are async, and `fetch` is not cached by default. Check `frontend/node_modules/next/dist/docs/` before using a framework API from memory — details in [docs/frontend-rules.md](docs/frontend-rules.md).

## Commands

```bash
cd backend  && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

cd backend  && uv run pytest
cd frontend && npm run lint
```

## Current state

Scaffold plus docs. Phase 0 of [docs/build-plan.md](docs/build-plan.md) is the next work.
