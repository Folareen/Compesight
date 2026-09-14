# Backend Rules

FastAPI service in [`backend/`](../backend/). Read [rules.md](rules.md) first — the universal rules apply here too, and rule 1 (workspace scoping) is enforced almost entirely in this codebase.

## Language and tooling

- **Python 3.12+.** Managed with `uv` — `uv add`, `uv run`, `uv sync`. Never bare `pip`.
- **Type hints on everything**, modern syntax: `list[str]`, `str | None`, `dict[str, Any]` — not `List`/`Optional`/`Dict`.
- **Config through [`app/config.py`](../backend/app/config.py) only.** No `os.getenv` scattered through modules — add a field to `Settings`. Every new setting gets an entry in `.env.example` in the same change.

## Layout

```
app/
  main.py          # app construction, middleware, router includes
  config.py        # Settings — the only place env is read
  api/             # routers, one module per resource
  models/          # SQLAlchemy models
  schemas/         # Pydantic request/response models
  repositories/    # workspace-scoped data access
  services/        # business logic, importable by routes and tasks
  tasks/           # Celery tasks — thin, delegate to services
  llm/
    prompts/       # versioned prompt files, not inline strings
```

The rule behind the layout: **a Celery task and a route must be able to call the same service.** Business logic never lives in a route handler or a task body — both are thin entry points. A manual crawl triggered from the dashboard and a scheduled one run identical code.

## Workspace scoping

The universal rule, made concrete:

- **Repository functions take `workspace_id` as a required argument.** Not optional, not defaulted, not pulled from a global. Forgetting it should be a `TypeError` at import-time-ish, not a silent leak at runtime.
- **Routes never read `workspace_id` from the request.** It comes from the verified Clerk session, resolved to a workspace context dependency.
- **A path id is an untrusted claim.** `GET /api/competitors/{id}` must confirm the competitor belongs to the session's workspace before returning it — and return **404, not 403**, when it doesn't. See [api-conventions.md](api-conventions.md).
- Don't write raw queries against workspace-scoped tables outside `repositories/`.

## API boundary

- **Pydantic models in both directions.** Never return an ORM object from a route — a column added later would leak silently. Never trust an unvalidated dict coming in.
- Request models never accept `workspace_id`, `id`, or server-owned timestamps.
- **Routers in `app/api/`**, one module per resource, included in `main.py` under `/api`. Match the shape of [`app/api/health.py`](../backend/app/api/health.py).
- Full conventions — status codes, pagination, errors — in [api-conventions.md](api-conventions.md).

## Async

- **Async by default for I/O**: routes, DB calls, HTTP, Playwright.
- **Never block the event loop.** A sync-only library goes in a worker thread (`anyio.to_thread.run_sync`), never called directly from an async route.
- Celery tasks are sync entry points; run async services inside them with a single explicit event loop per task, not nested loops.

## Database

- **Migrations for every schema change** (Alembic). No hand-edited DB state. No `create_all` outside tests.
- Timezone-aware UTC columns. Money as integer minor units + currency code.
- Add the indexes named in [data-model.md](data-model.md) when you create the table, not after the timeline query gets slow.
- Deleting a workspace removes every row carrying its `workspace_id` — an explicit, tested routine, not an assumption about cascades.

## Jobs

- **Assume every task runs at least twice.** Retries, redeploys, at-least-once delivery. Idempotency keys per [scraping.md](scraping.md).
- Each pipeline stage is its own task, so a failure is retryable at the stage that failed.
- Exponential backoff with jitter. Never let one bad source stall a queue.
- Tasks take ids, not objects — a serialized ORM object is stale by the time the worker picks it up.

## LLM calls

- Only on the job path. **Never in a request handler.**
- Schema-validate every response before it touches the DB.
- Write an `llm_usage` row on every call, no exceptions.
- Prompts live in `app/llm/prompts/` as versioned files. Record which version produced a finding.
- Full guidance in [llm-usage.md](llm-usage.md).

## Code simplicity

The governing rule, and the one everything below follows from:

> **Validate untrusted data once at the boundary. Trust typed application code everywhere else.**

Defensive code belongs at the edges — scraped HTML, LLM responses, source APIs, webhooks, env vars. Past that point the shape is known, and re-checking it adds noise while hiding real bugs.

This matters here more than in most codebases: nearly everything we handle arrives untrusted, so the temptation is to let `Any` and `dict[str, Any]` leak inward from the crawl layer all the way to the dashboard. Don't.

### Don't let `Any` travel inward

Be suspicious of `Any`, `dict[str, Any]`, `Mapping[str, Any]`, and `object` in normal application logic. An extraction result is jsonb in the database, but it becomes a typed model the moment it's read — a dataclass or Pydantic model with real fields, not a dict threaded through `services/` and `tasks/`.

A function that takes a dict and picks a field out of it with `isinstance` guards and a `""` fallback is the shape to avoid: it defers the typing problem rather than solving it, and the fallback invents data. Parse at the boundary, then pass the model.

### No generic converters or extractor helpers

Treat `as_string`, `to_int`, `safe_get`, `ensure_dict`, `normalize_value`, `extract_id`, `coerce_*` as smells. They exist to compensate for a type that's too broad upstream — fix the type instead and the helper disappears.

Ask "what is this value actually supposed to be?" A competitor's domain is a `str`. A tier price is an `int` of minor units. Neither should ever be "whatever arrives, coerced".

### No silent empty fallbacks

`return ""`, `return {}`, `return []`, `value or {}`, `data.get("field", "")` — all fine when absence is genuinely valid, all dangerous when they paper over an invalid state.

This one has teeth in this product. A pricing extraction that silently returns `{}` on a malformed page doesn't look like a failure; it looks like *the competitor removed all their pricing tiers*, and that fires a false high-urgency alert. Raise, or mark the source `degraded` — never degrade invalid state into a plausible-looking empty value. [rules.md](rules.md): silence is never success.

### Catch exceptions you can handle

- No bare `except:`. No reflexive `except Exception` that returns `None`.
- Never catch-and-re-raise unchanged — delete the `try`.
- Don't log-and-re-raise at every layer; log once at the boundary that owns the failure.
- Prefer a library's real exception (`DuplicateKeyError`, `httpx.TimeoutException`) over inspecting `.code` on a generic one.

Crawl failures are the exception that proves the rule: they're *expected*, genuinely recoverable, and handled deliberately by the health state machine in [scraping.md](scraping.md). That's real error handling. `except Exception: return None` is not.

### Trust the model after validation

An LLM response is untrusted until schema-validated — then it's a typed object, and code downstream shouldn't re-check `isinstance(finding.urgency, str)`. Same for Pydantic request models and ORM rows: validate once, at the boundary, then trust the type. If the type is wrong, fix the type rather than guarding every call site.

### Don't add layers that only forward

`Controller → Service → Manager → Processor → Repository` where most layers pass arguments through is ceremony, not architecture. The layout in this doc has exactly three meaningful layers — route/task, service, repository — and a new one needs to earn its place with real behaviour: policy, orchestration, mapping, or a genuine boundary.

Related smells: base classes and mixins that centralise two utility methods, `Protocol`/`ABC` with one implementation, factories where construction is a constructor call, builders where a dataclass literal would do, and DI containers where `ProjectService(repo, logger)` works.

### Keep it boring

- **Early returns** over nested `if`. Keep the happy path at one indent level.
- **No helper explosion** — a one-line, one-caller function that only does `.strip()` or reads a field should be inlined. A helper should name a real concept.
- **No useless intermediates**: `domain = event.domain.strip().lower()`, not three variables to get there.
- **Comments explain why**, not what. Delete `# check if project exists`. Keep the note about why a competitor's pricing page needs a 5-second settle before extraction.
- **Docstrings for real contracts**, not `"""Get a project."""` on `get_project`.
- Don't make functions `async` when they do no I/O. Don't `create_task` fire-and-forget without owning the lifecycle.

### What to preserve

This is about removing *fake* defensiveness, never real safety. Keep every check that guards genuine uncertainty:

crawl failures and timeouts · malformed HTML · malformed or truncated LLM output · robots.txt and rate-limit handling · source-API errors · database not-found · nullable columns that are genuinely nullable · webhook delivery failures · **every authorization and workspace-scoping check**

> Defend against external uncertainty, not against your own typed code.

## Errors and logging

- Never leak internal exceptions, SQL, or stack traces in a response — see the error shape in [api-conventions.md](api-conventions.md).
- **Never log secrets, scraped credentials, cookie jars, or request headers.** Crawl logging is verbose and ends up in aggregators.
- Log URLs, status codes, durations, and ids. Structured, not f-string prose.

## Tests

`uv run pytest`. Real Postgres, never SQLite — jsonb, enums, and pgvector don't exist there. No live LLM calls, no live crawls. Full policy and the must-have test list in [rules.md](rules.md#testing).
