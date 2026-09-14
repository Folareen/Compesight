# Compesight

Competitor monitoring web app. See [spec.md](spec.md) for the full product spec, and [docs/](docs/) for architecture, conventions, and the build plan.

## Stack

- `frontend/` — Next.js (App Router, TypeScript, Tailwind)
- `backend/` — FastAPI (Python, managed with [uv](https://docs.astral.sh/uv/))

## Getting started

### Infra (Postgres + Redis)

```bash
docker compose up -d
```

### Backend

```bash
cd backend
cp .env.example .env   # fill in Clerk keys
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Celery worker (separate terminal):

```bash
cd backend
uv run celery -A app.celery_app worker --loglevel=info
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
cp .env.example .env.local   # fill in Clerk keys
npm install
npm run dev
```

App: http://localhost:3000

### Tests

```bash
createdb compesight_test   # once
cd backend && uv run pytest
cd frontend && npm run lint
```
