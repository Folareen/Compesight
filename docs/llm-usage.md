# LLM Usage

Four jobs: extraction fallback, classification, battlecard maintenance, Q&A. Every one of them runs on the job path, never in a request.

## Models

Default to the latest Claude models. Match model to job rather than using one everywhere — classification runs on every diff and dominates volume.

| Job | Model | Why |
|---|---|---|
| Significance filter | **none** | Rules, not a model. See below. |
| Classification | Haiku-class | High volume, narrow task, schema-constrained |
| Extraction fallback | Sonnet-class | Messy input, structure matters |
| Battlecard | Sonnet-class | Low volume, quality matters, user-visible prose |
| Q&A | Sonnet-class | User-facing, cites sources |

Model IDs are config in `Settings`, never hardcoded at call sites. When touching model choice or pricing, consult the `claude-api` skill rather than recalling from memory.

## Rule 1: don't call a model

The cheapest call is the one not made. Before classification, a **significance filter** drops:

- whitespace, entity, and attribute-order churn
- reordered lists with identical members (rotating testimonials, shuffled logos)
- copyright years, "last updated" stamps, cache-busting query strings
- session ids, CSRF tokens, analytics params
- changes confined to fields marked `ignore` in the source config

Also short-circuit earlier: identical `content_hash` skips extraction entirely, and selector-based extraction avoids the extraction model whenever the page cooperates.

Get this right before tuning prompts. It's the difference between a viable margin and not.

## Rule 2: model output is untrusted input

Every call returns schema-validated structured output. Then:

- **Validate before persisting.** Never `json.loads` and write.
- **On malformed output:** retry once, then mark the finding `classification_failed`. Never drop the finding — the diff is durable and real; only the label is missing.
- **Constrain enums.** `change_type` and `urgency` come from fixed sets. An unknown value is a validation failure, not a new category.
- **Never let a model decide alerting directly.** It assigns urgency; routing rules — deterministic, user-controlled — decide who gets told.

## Classification

Input is the field-level changeset, not the raw page. Feeding whole pages is expensive and *worse*: the diff is already the signal.

Include: competitor name, source type, changed fields with before/after, and a short excerpt of surrounding context.

Urgency guidance, in the prompt and in the product:

- **high** — competitor changed pricing, launched a competing feature, announced funding or acquisition.
- **medium** — notable positioning or messaging shift, significant content or product update.
- **low** — routine content, minor copy, hiring, small cosmetic change.

**Per-workspace few-shot examples come from `finding_feedback`.** Corrections are the tuning mechanism — no fine-tuning in v1. Cap the examples included so the prompt doesn't grow without bound; prefer recent corrections and ones matching the current source type.

## Extraction fallback

Only when selectors fail or drift. Always record `method` on the extraction so drift is measurable — a source whose selectors have quietly stopped working is `degraded` even though its fetches succeed.

Ask for a fixed schema per source type (pricing tiers, feature lists, headline copy). A free-form "extract what matters" output cannot be diffed at the field level, which defeats the entire approach.

## Battlecard maintenance

Update incrementally from new findings — never regenerate from full history, which is expensive and causes unprompted rewrites of sections nothing changed.

Write a `battlecard_revision` on every change and link each section to the finding that changed it. A self-rewriting document without provenance is not trustworthy.

## Q&A

RAG over findings. **Workspace filter belongs in the SQL `WHERE`, not applied to results afterwards.** Answers cite the findings they used; users can open the underlying diff. If retrieval returns nothing relevant, say so — never answer from the model's own knowledge of the competitor.

## Cost control

- Write an `llm_usage` row on **every** call. No exceptions — budget enforcement without complete data is guesswork.
- Per-workspace monthly budget: soft warn, then hard stop.
- **Hard stop queues classification; it does not drop it.** Crawling and diffing continue, findings stay durable, and the workspace is told. Classification resumes when the budget resets or is raised.
- Cap input size per call. A pathological page must not produce a pathological bill.

## Prompts

Live in versioned files under `app/llm/prompts/`, not inline strings. Record which prompt version produced a finding — when classification quality shifts, that's the first thing to check.
