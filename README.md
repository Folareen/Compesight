# Compesight

Competitor monitoring web app. See [spec.md](spec.md) for the full product spec, and [docs/](docs/) for architecture, conventions, and the build plan.

## Stack

- `frontend/` — Next.js (App Router, TypeScript, Tailwind)
- `backend/` — FastAPI (Python, managed with [uv](https://docs.astral.sh/uv/))

## Getting started

### Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App: http://localhost:3000
