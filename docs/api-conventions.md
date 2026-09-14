# API Conventions

REST-ish over JSON under `/api`. Routers in `app/api/`, one module per resource, included in [`main.py`](../backend/app/main.py).

## Shape

```
GET    /api/competitors
POST   /api/competitors
GET    /api/competitors/{id}
PATCH  /api/competitors/{id}
DELETE /api/competitors/{id}

GET    /api/competitors/{id}/sources
POST   /api/competitors/{id}/sources
GET    /api/competitors/{id}/battlecard

GET    /api/findings?competitor_id=&change_type=&urgency=&since=&cursor=
POST   /api/findings/{id}/feedback

GET    /api/sources/{id}/health
POST   /api/sources/{id}/crawl        # manual trigger, enqueues a job

GET    /api/routing-rules
PUT    /api/routing-rules
GET    /api/channels
POST   /api/channels
```

Plural nouns. Nest only one level deep — deeper nesting gets a top-level resource with a filter instead.

## Workspace scoping

**The workspace is never in the URL or body.** It comes from the verified session. A resource id in a path is an untrusted claim until checked against the session's workspace — see [rules.md](rules.md).

A resource belonging to another workspace returns **404, not 403.** 403 confirms the id exists, which leaks information across tenants.

## Status codes

`200` read/update · `201` create · `202` accepted (job enqueued) · `204` delete · `400` malformed · `401` unauthenticated · `403` authenticated but not permitted *within* your workspace (e.g. member attempting an owner action) · `404` missing or not yours · `409` conflict · `422` validation (FastAPI default) · `429` rate limited.

`202` matters here: anything triggering a crawl or classification returns immediately with a job reference. Routes never block on the job path.

## Errors

```json
{ "error": { "code": "source_blocked", "message": "robots.txt disallows crawling this path.", "details": {} } }
```

`code` is a stable machine-readable string; `message` is human-readable and safe to display. Never leak internal exceptions, SQL, or stack traces.

## Pagination

Cursor-based on all list endpoints — findings grow without bound and offset pagination skips rows when new ones arrive mid-scroll.

```json
{ "data": [...], "next_cursor": "opaque", "has_more": true }
```

Default 50, max 200.

## Validation

Pydantic models both directions. Request models never accept `workspace_id`, `id`, or any server-owned timestamp. Response models are explicit — never return an ORM object directly, or private fields leak the moment a column is added.

## Naming

`snake_case` in JSON, matching Python. The frontend does not transform it; consistency beats convention-matching on each side.

Timestamps are ISO 8601 UTC with an offset: `2026-09-14T10:30:00Z`.

## Frontend consumption

Server Components fetch server-side with the session token. **`fetch` is not cached by default in Next 16** — it blocks render until complete. Wrap slow reads in `<Suspense>`, or opt into `use cache` for genuinely static data. Verify against `frontend/node_modules/next/dist/docs/` rather than memory.

Mutations go through Server Actions or route handlers that forward to FastAPI — never call the backend directly from a Client Component with a token in the browser.
