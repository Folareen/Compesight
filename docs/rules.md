# Rules

Universal rules — they apply to every part of the codebase. Non-negotiable: if one blocks something genuinely necessary, change the rule in the same PR with a reason, don't quietly break it.

Stack-specific conventions live separately:

- **[backend-rules.md](backend-rules.md)** — FastAPI, Python, jobs, database
- **[frontend-rules.md](frontend-rules.md)** — Next.js 16, React, styling

## The three that cause real damage

### 1. Every workspace-scoped query filters on `workspace_id`
No exceptions. A missing filter is a cross-tenant data leak, not a bug.

- Never accept `workspace_id` from a request body, query param, or client-supplied header. Derive it from the authenticated session, always.
- A resource id in a URL is an *untrusted claim* until checked against the session's workspace.
- Another workspace's resource returns **404, not 403** — 403 confirms the id exists.
- Enforcement details are in [backend-rules.md](backend-rules.md); the frontend must never compensate by filtering client-side.

### 2. Never log or expose secrets, scraped credentials, or raw session tokens
Crawl logs are verbose and end up in aggregators. Log URLs and status codes, never request headers or cookie jars. Never put a secret anywhere the browser can read it.

### 3. Respect the sites we crawl
robots.txt, rate limits, and backoff are product requirements, not niceties — see [scraping.md](scraping.md). Getting our crawler IP-banned breaks the product for every customer at once. Never add a "just ignore robots for this one site" flag.

## Data and correctness

These hold on both sides of the wire.

- **All timestamps UTC**, stored timezone-aware, converted for display only. Users span timezones and digests are scheduled — naive datetimes will cause real bugs.
- **Money as integer minor units** plus a currency code. Never floats. Competitor pricing is core data and `49.99` is not exactly representable.
- **Crawls and jobs are idempotent.** Assume every job runs at least twice; re-running must not duplicate findings or alerts.
- **An LLM response is untrusted input.** Validate against a schema before it touches the DB. Never `json.loads` a model response and hope.
- **Silence is never success.** A source that fails to crawl is `failing`, never "no changes found" — in the data, in the API, and in the UI.

## Code simplicity

> **Validate untrusted data once at the boundary. Trust typed application code everywhere else.**

Almost everything this product handles arrives untrusted — scraped HTML, LLM output, third-party APIs, user input — so the pull toward defensive code everywhere is strong. Resist it. Defensive checks belong at the edge; past that point the shape is known, and re-checking it adds noise while hiding real bugs.

The failure this prevents is specific and expensive: code that turns an invalid state into a plausible-looking empty value. An extraction that silently returns `{}` on a malformed page doesn't read as a failure — it reads as *the competitor deleted all their pricing tiers*, and fires a false high-urgency alert. Raise, or mark the source `degraded`. Never degrade.

The corollary, which matters just as much: **don't strip real defensiveness.** Crawl failures, malformed model output, nullable columns, delivery errors, and every authorization check are genuine uncertainty and stay.

Per-stack specifics — what to avoid, what to preserve, with examples — are in [backend-rules.md](backend-rules.md) and [frontend-rules.md](frontend-rules.md).

## Testing

Test what breaks quietly — tenancy, diffing, idempotency, LLM output handling — not CRUD routes.

Must have:
1. **Workspace isolation** — two-workspace fixture, assert B can't read/write A's rows and a foreign id returns 404, not 403. The suite's reason for existing.
2. **Diffing**, table-driven on real captured HTML — false positives (reordered testimonials, copyright rollover, whitespace churn) must produce **no** finding; real changes must produce exactly one.
3. **Idempotency** — run each pipeline stage twice, assert no duplicate snapshots, findings, or alerts.
4. **LLM response handling** (mocked) — malformed JSON, invalid enum values, timeouts; assert the finding survives as `classification_failed`, nothing invalid is persisted.
5. **Routing resolution** — specificity order, mutes, and cross-source dedupe.

Rules:
- Never call a real LLM or crawl a live site in tests — fixture responses, captured pages served locally. Deterministic and free.
- Real Postgres, not SQLite — jsonb, enums, and pgvector don't exist there. Migrations applied, never `create_all`.
- Time is injected, never read inline — scheduling and digest windows are untestable otherwise.
- Not worth testing: framework behaviour, Pydantic validation itself, thin CRUD, exact LLM prose (assert structure, never wording).
- Frontend: light. Component tests for stateful pieces (routing rule editor, feedback buttons); one end-to-end path (sign in → add competitor → see baseline) beats broad shallow coverage.

```bash
cd backend && uv run pytest
cd frontend && npm run lint
```

Both must pass before a change is done.

## Git

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Don't commit `.env`. `.env.example` stays current with every new setting.
- The `<!-- BEGIN:nextjs-agent-rules -->` block in [`frontend/AGENTS.md`](../frontend/AGENTS.md) is generated by `next dev`. Commit it with your work; deleting it just re-creates an uncommitted change.

## When unsure

Ask, or write the smallest version that works and flag it. Do not invent a competitor data source, a pricing model, or a schema decision the spec doesn't cover — [spec.md](../spec.md) has an Open Questions section, and that's where unresolved things belong.
