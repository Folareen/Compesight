# Data Model

Postgres. Every table below except `user` is workspace-scoped and carries `workspace_id` — see [rules.md](rules.md).

Conventions: UUID primary keys; `created_at`/`updated_at` timezone-aware UTC on every table; money as integer minor units + currency code; enums as Postgres enum types.

## Identity and tenancy

**`user`** — `id`, `clerk_user_id` (unique), `email`, `name`, `created_at`.
Mirrors a Clerk user. Clerk owns authentication; this row exists so we can foreign-key to something stable.

**`workspace`** — `id`, `name`, `slug` (unique), `plan`, `llm_budget_cents_monthly`, `created_at`.

**`workspace_member`** — `id`, `workspace_id`, `user_id`, `role` (`owner` | `member`), `created_at`.
Unique on `(workspace_id, user_id)`. Authorization joins through here, always.

## Monitoring

**`competitor`** — `id`, `workspace_id`, `name`, `website_url`, `status` (`pending` | `active` | `muted`), `muted_until`, `created_at`.

**`source`** — `id`, `workspace_id`, `competitor_id`, `type`, `url`, `config` (jsonb), `crawl_interval_seconds`, plus health:
`status` (`healthy` | `degraded` | `failing` | `blocked`), `last_attempt_at`, `last_success_at`, `consecutive_failures`, `blocked_reason`.

`type` ∈ `website`, `pricing_page`, `rss`, `reddit`, `hackernews`, `producthunt`, `youtube`, `github`, `appstore`, `playstore`.

Pricing pages are their own source type, not a flag — they need their own interval and their own extraction schema.

**`snapshot`** — `id`, `workspace_id`, `source_id`, `fetched_at`, `content_hash`, `raw_payload`, `raw_payload_dropped_at`, `http_status`, `error`.

The expensive table. Retention: drop `raw_payload` after 30 days (set `raw_payload_dropped_at`), keep the row. **Always keep the most recent successful snapshot per source regardless of age** — it's the diff baseline.

`content_hash` short-circuits the pipeline: identical hash means no extraction, no diff, no LLM call.

**`extraction`** — `id`, `workspace_id`, `snapshot_id`, `schema_version`, `fields` (jsonb), `method` (`selector` | `llm` | `mixed`), `confidence`.

`method` drives the extraction-drift health signal: selectors silently giving way to LLM fallback means the page changed shape.

## Findings

**`finding`** — `id`, `workspace_id`, `competitor_id`, `source_id`, `snapshot_id`, `change_type`, `urgency` (`high` | `medium` | `low`), `title`, `summary`, `changeset` (jsonb), `is_baseline`, `dedupe_key`, `classification_status`, `detected_at`.

`change_type` ∈ `pricing`, `feature_launch`, `messaging`, `hiring`, `funding`, `partnership`, `content`, `other`.

- `changeset` holds the field-level before/after — the evidence. The timeline links back through `snapshot_id` so users can verify rather than trust the summary.
- `is_baseline` findings populate battlecard and timeline but never alert.
- `dedupe_key` collapses the same real-world change seen via two sources.
- `classification_status` (`ok` | `pending` | `failed`) lets a finding exist durably while classification is retried or budget-parked.

**`finding_feedback`** — `id`, `workspace_id`, `finding_id`, `user_id`, `verdict` (`useful` | `noise`), `corrected_change_type`, `corrected_urgency`, `created_at`.

Feeds per-workspace few-shot examples and the "mute this type?" suggestion. See [llm-usage.md](llm-usage.md).

## Alerts

**`routing_rule`** — `id`, `workspace_id`, `competitor_id` (nullable = workspace default), `change_type` (nullable = all), `min_urgency`, `channels` (array), `enabled`.
Most specific match wins: competitor+type, then competitor, then workspace+type, then workspace default.

**`notification_channel`** — `id`, `workspace_id`, `kind` (`email` | `slack` | `webhook`), `config` (jsonb), `verified_at`.
Webhook secrets and Slack tokens live here — encrypted at rest, never logged.

**`alert`** — `id`, `workspace_id`, `finding_id`, `channel_id`, `status` (`pending` | `sent` | `failed`), `attempts`, `last_error`, `sent_at`.
Separate from `finding` so delivery can fail and retry without touching the finding.

**`digest`** — `id`, `workspace_id`, `period_start`, `period_end`, `sent_at`, `finding_ids`.

## Battlecard and Q&A

**`battlecard`** — `id`, `workspace_id`, `competitor_id` (unique), `positioning`, `strengths`, `weaknesses`, `pricing_tiers` (jsonb), `updated_at`, `version`.

**`battlecard_revision`** — `id`, `workspace_id`, `battlecard_id`, `version`, `content` (jsonb), `triggered_by_finding_id`, `created_at`.
Keep history. An LLM-maintained document that silently rewrites itself is untrustworthy; users need to see what changed and why.

**`finding_embedding`** — `id`, `workspace_id`, `finding_id`, `embedding` (pgvector), `chunk_text`.
`pgvector` in the main database, not separate infra. Q&A retrieval filters on `workspace_id` **in the SQL**, never post-filters results.

## Cost tracking

**`llm_usage`** — `id`, `workspace_id`, `purpose`, `model`, `input_tokens`, `output_tokens`, `cost_cents`, `created_at`.
Every model call writes a row. Without this, budget enforcement is guesswork.

## Indexes that matter

- `(workspace_id, competitor_id, detected_at DESC)` on `finding` — the timeline query.
- `(workspace_id, dedupe_key)` on `finding` — deduplication lookup.
- `(status, last_attempt_at)` on `source` — the scheduler's due-sources query.
- `(source_id, fetched_at DESC)` on `snapshot` — fetching the diff baseline.
- `(workspace_id, created_at)` on `llm_usage` — budget rollups.

## Deletion

Deleting a competitor cascades to sources, snapshots, extractions, findings, battlecard. Deleting a **workspace** must remove every row carrying its `workspace_id` — write it as an explicit, tested routine, not an assumption about cascades.
