# Build Plan

Ordered so there's something demonstrable early, and so the expensive/uncertain parts (extraction quality, classification relevance) get exercised before everything else is built on top of them.

Each phase names its **done** condition. Don't move on without it.

---

## Phase 0 — Foundations
Current state: bare scaffold, health endpoint only.

- Postgres + migrations (Alembic). Redis + Celery, with one trivial task proving the worker runs.
- `user` / `workspace` / `workspace_member` tables.
- Clerk wired: sign-up, sign-in, session. Backend verifies the JWT and resolves a workspace context.
- **The workspace-scoped query helper** — the thing every later query goes through. Build it now, before there's anything to leak.
- Dashboard shell: nav, auth-gated layout, design tokens from [design-system.md](design-system.md) applied.

**Done when:** a new user signs up, lands on an empty dashboard, and a Celery task runs to completion.

---

## Phase 1 — Website monitoring, end to end
The anchor feature. One source type, full pipeline, no LLM yet.

- `competitor` + `source` CRUD.
- Playwright crawl for `website` and `pricing_page`; `snapshot` rows with `content_hash`.
- Selector-based extraction → `extraction` rows.
- Field-level diff → `finding` rows (mechanically typed for now, no classification).
- Scheduler enqueues due sources with jitter.
- Competitor detail page with a change timeline and `DiffView`.

**Done when:** add a competitor, its pricing page is crawled on a schedule, and a real price change appears in the timeline with a before/after diff.

This is the riskiest phase. Extraction against real sites is where the surprises live — budget accordingly.

---

## Phase 2 — Baseline and source health
Both are what make Phase 1 trustworthy rather than a demo.

- Baseline crawl on competitor add; `is_baseline` findings; `pending` → `active` status.
- Source discovery: probe the domain for RSS, `/blog`, `/changelog`, GitHub org. User confirms each.
- Health state machine: `healthy` / `degraded` / `failing` / `blocked`, with backoff and robots.txt handling.
- Extraction-drift signal (selectors → LLM fallback rate).
- The three distinct `EmptyState` cases.

**Done when:** adding a competitor produces useful content within a minute, and breaking a selector surfaces a visible `failing` state rather than silence.

---

## Phase 3 — LLM classification
First model calls. See [llm-usage.md](llm-usage.md).

- Significance filter **before** classification — drops whitespace, reordering, rotating testimonials. Cheapest possible win; do it first.
- Classification: change type + urgency, schema-validated.
- LLM extraction fallback for pages selectors can't handle.
- `llm_usage` tracking from the very first call.
- Feedback buttons on findings → `finding_feedback`.

**Done when:** findings carry sensible types and urgencies, every call is cost-tracked, and a malformed model response fails safe instead of corrupting a row.

---

## Phase 4 — Alerts
Findings become something you don't have to log in to see.

- `notification_channel` (email, Slack, webhook) with verification.
- `routing_rule` with specificity resolution; mutes.
- Deduplication via `dedupe_key`.
- Delivery with independent retry; `alert` rows.
- Weekly digest.

**Done when:** a high-urgency pricing change reaches Slack within minutes, a muted type doesn't, and the same change from two sources arrives once.

---

## Phase 5 — Battlecards
- LLM-maintained battlecard per competitor, updated as findings land.
- `battlecard_revision` history, with each section linking to the finding that changed it.
- `BattlecardPanel` UI.

**Done when:** a pricing change updates the battlecard's pricing tiers and the change is traceable to its finding.

---

## Phase 6 — More sources
Now the pipeline is proven, sources are mostly adapters. Roughly easiest-first:

RSS/blog → GitHub → Hacker News → Reddit → Product Hunt → YouTube → App Store / Play.

**Done when:** each writes snapshots through the same pipeline. Any source needing its own diff or classification path is a design smell — fix the abstraction instead.

---

## Phase 7 — Q&A
- `pgvector`, embeddings on findings, workspace-filtered retrieval **in SQL**.
- Chat UI per competitor, answers citing the findings they came from.

**Done when:** "did they change pricing this quarter?" returns a cited answer, and no query can reach another workspace's rows.

---

## Phase 8 — Commercial
- Plans, Stripe, workspace subscription.
- Plan-bound crawl intervals and competitor limits.
- LLM budget enforcement: soft warn, hard stop that queues classification rather than dropping it.
- Snapshot retention job (30-day raw payload drop, keep latest per source).
- Google Sheets / Docs export.

**Done when:** a free workspace is genuinely limited, and exceeding budget degrades gracefully with the user informed.

---

## Ordering notes

- **Phases 1–3 are the product.** If something has to give, cut sources (6) and Q&A (7), not health (2) or dedup/routing (4).
- Retention (8) only matters once snapshots accumulate, but the *schema* for it lands in Phase 1 — retrofitting a retention column across a large table is painful.
- Billing last, deliberately. It's well-understood work; nothing is learned by doing it early.
