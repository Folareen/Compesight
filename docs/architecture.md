# Architecture

## Shape

One FastAPI service, one Next.js dashboard, one Postgres, one Redis + Celery for jobs. Deliberately boring — the hard problems here are extraction quality and alert relevance, not distributed systems.

```
Next.js dashboard ──HTTP──► FastAPI ──► Postgres
                               │
                               ├──► Redis ──► Celery workers ──► Playwright / source APIs
                               │                    │
                               │                    └──► LLM provider
                               └──► Clerk (identity)
```

The API process and the Celery workers run **the same codebase**, so extraction and classification logic is imported by both. A crawl triggered manually from the dashboard runs the identical code path as a scheduled one.

## Request path vs. job path

The split that matters most:

- **Request path** (FastAPI routes) is read-mostly and must stay fast. It never crawls, never calls an LLM synchronously, never blocks on a competitor's slow server.
- **Job path** (Celery) does everything slow: crawling, extraction, classification, battlecard updates, digests.

When a user adds a competitor, the route writes the rows and enqueues a baseline job, then returns immediately. The dashboard shows the competitor in a `pending` state and fills in as jobs land.

## The pipeline

Each stage is a separate Celery task, so a failure is retryable at the stage that failed rather than from the top.

```
schedule ─► crawl ─► extract ─► diff ─► classify ─► route ─► deliver
                                 │         │
                                 └─► (no significant change) drop
                                           │
                                           └─► update battlecard, index for Q&A
```

1. **schedule** — beat process enqueues due sources. Due = `now >= last_attempt_at + interval`, skipping `blocked` sources and muted competitors.
2. **crawl** — fetch. Playwright for pages, plain HTTP for feeds and APIs. Writes a `snapshot` row with the raw payload, or records a failure and updates source health. See [scraping.md](scraping.md).
3. **extract** — snapshot → structured fields. Selectors first, LLM fallback. Writes `extraction` rows.
4. **diff** — compare structured fields against the previous successful extraction. Produces a field-level changeset, or nothing. Insignificant diffs (see [llm-usage.md](llm-usage.md)) are dropped **before** classification so they never cost a model call.
5. **classify** — LLM assigns change type and urgency, writes a `finding`.
6. **route** — apply the workspace's routing rules, mutes, and deduplication to decide channels. Writes `alert` rows.
7. **deliver** — send email / Slack / webhook, with retries. Delivery failure never loses the finding; the finding is already durable.

Stages 5–7 are skipped for baseline findings, which populate the battlecard and timeline without alerting.

## Why crawls are isolated per workspace

Decided in the spec: each workspace gets its own Source rows and snapshot history, even for an identical URL. Cross-tenant leakage becomes structurally impossible, at the cost of duplicated crawl and extraction spend.

The important architectural consequence: **findings were never shared**, so a shared snapshot cache keyed on `(normalized_url, fetch_window)` can be slid in underneath later as a pure optimization, without touching ownership. Keep crawl/extract free of workspace-specific logic so that stays true — workspace concerns belong in the diff stage and later.

## Scheduling

- Celery beat enqueues due sources on a short tick.
- **Intervals are plan-bound**, not arbitrary. Cost control, per the spec.
- **Jitter every interval.** Without it, every source added on signup day stampedes together forever.
- A source already running is never enqueued twice — lock on source id.

## Failure policy

- **Crawl failures are expected**, not exceptional. Sites go down, rate-limit, redesign. Retry with exponential backoff, increment `consecutive_failures`, transition health state. Never let one bad source stall a queue.
- **`blocked` is terminal** until a human or a much slower re-probe clears it. Never retried on the normal schedule.
- **LLM failures retry with backoff**, then park the finding as `classification_failed` rather than dropping it. The diff is already durable; classification can be re-run.
- **Delivery failures retry independently** of everything upstream.

## Auth

Clerk owns identity — users, sign-in, social login, sessions. **We own workspaces, membership, and all authorization.**

- Clerk is the source of truth for *who you are*; Postgres is the source of truth for *what you may see*.
- A `user` row keys to a Clerk user id. `workspace` and `workspace_member` are ours.
- The backend verifies the Clerk JWT on every request and resolves it to a workspace context. Never trust a `workspace_id` from the client — see [rules.md](rules.md).
- In Next.js, Proxy handles optimistic redirects only. Real checks happen server-side at data access.

## What we are deliberately not doing in v1

- No microservices. One service, split later along the request/job seam if ever needed.
- No Kubernetes. Containers on a managed host.
- No vector DB as separate infra — `pgvector` in the existing Postgres for Q&A.
- No websockets. "Real-time alerts" means push to email/Slack/webhook; the dashboard polls.
- No self-hosted models. See [llm-usage.md](llm-usage.md).
