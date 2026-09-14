# Compesight — Spec

## What it is
A web app that monitors competitors' websites and public online presence, detects changes, classifies them with an LLM, and surfaces them as alerts and a running battlecard per competitor.

## Format
Full web app with a dashboard. Not a bare API service.

## Accounts and Tenancy
- A **User** signs in and belongs to one or more **Workspaces**. All competitors, sources, findings, alerts, and battlecards belong to a Workspace, never directly to a User.
- Roles for v1 are minimal: `owner` and `member`. Owners manage billing and membership; members can do everything else. No per-competitor permissions in v1.
- Every workspace-owned table carries `workspace_id`, and every query filters on it. This is the one thing not worth retrofitting later.
- **Crawls are fully isolated per workspace.** If two workspaces both monitor `stripe.com/pricing`, each gets its own Source row, its own crawl schedule, and its own snapshot history. The same page is fetched and extracted once per workspace.
  - Accepted cost: duplicated crawl traffic and duplicated LLM extraction spend for overlapping competitors.
  - Bought benefit: no cross-tenant leakage is structurally possible, and per-workspace crawl intervals, auth'd pages, and extraction overrides stay trivial.
  - Revisit if overlap gets expensive. A shared snapshot cache keyed on (normalized URL, fetch window) can be slid underneath later *without* changing the ownership model, because findings were never shared to begin with.

## Core Input
- User adds a competitor by website URL.
- Optional: separate pricing page URL (tracked on its own since it updates on a different cadence than the main site).
- Website monitoring is the anchor feature. It works for every competitor regardless of industry. Every other source below is optional and added per competitor where relevant.

## Sources
- Website / pricing page (headless browser crawl, structured diffing)
- RSS / blog (feed parsing)
- Reddit (public API)
- Hacker News (public API)
- Product Hunt (public API)
- YouTube channel uploads (public Data API)
- GitHub releases / changelog / issue activity (public API)
- App Store / Google Play release notes and version history

### Stretch
- Discord (bot reading public channels of a competitor's community server, only if one exists)
- X/Twitter (official API is paid and restrictive, unofficial scraping is fragile)
- LinkedIn (heavy anti-bot protection, against terms)

## Core Loop
1. User adds a competitor and its sources.
2. Scheduled jobs crawl each source on an interval.
3. New snapshot is diffed against the last one, at the structured-field level (e.g. "Pro tier price changed from $49 to $59"), not raw HTML diffing.
4. Diffs and new mentions are passed to an LLM for classification: type of change (pricing, feature launch, messaging, hiring, funding, etc.) and urgency level.
5. High/medium urgency items trigger a real-time alert (email or webhook). Everything else rolls into a weekly digest.
6. Each competitor has a persistent, LLM-maintained battlecard (strengths, weaknesses, positioning, pricing tiers) updated as new findings come in.
7. Natural language Q&A over accumulated findings per competitor (RAG over the monitoring history).

## Data Extraction and Scraping (headline feature)
- Headless browser layer (Playwright) for JS-rendered pages, not just static HTML fetches.
- Structured extraction from unstructured pages: rule-based selectors first, LLM-assisted extraction as fallback when page structure varies or breaks.
- Structured-field diffing, not raw text diffing.
- Polite crawling: respects robots.txt, backoff on failures, rate limiting.

## Real-Time Alerts
- Event-driven, not purely scheduled.
- LLM assigns urgency at classification time.
- High/medium urgency: immediate push (email/webhook).
- Low urgency: batched into weekly digest.

## Onboarding and First-Run Backfill
The first snapshot of a source has nothing to diff against, so a naive build shows an empty dashboard until a competitor happens to change something — possibly weeks. v1 must produce value in the first minute instead.

- On adding a competitor, immediately crawl the main site and pricing page, run structured extraction, and generate the **initial battlecard** (positioning, pricing tiers, claimed features) from that first snapshot.
- Present this as "here's what we see today" — a baseline, explicitly not a change.
- **Source discovery:** from the domain alone, probe for and suggest likely sources — `/blog`, `/changelog`, RSS `<link rel=alternate>`, a GitHub org matching the company name, a YouTube channel, App Store / Play listings. User confirms or dismisses each; nothing is monitored without confirmation.
- Baseline findings are marked `is_baseline` so they populate the battlecard and timeline but never fire a real-time alert.

## Alert Routing and Notification Settings
"Email or webhook" is not a configuration. Without per-type routing the product is noisy on day one.

- **Channels:** email, webhook, and Slack. Slack is the realistic default for a competitive-intel team and should not be deferred to a "later" pile.
- **Routing rules** live at the Workspace level, with optional per-competitor overrides. A rule is `(change_type, min_urgency) -> [channels]`.
  - Example: pricing changes at any urgency go to Slack immediately; hiring changes only appear in the weekly digest; everything else follows the default high/medium threshold.
- **Mutes:** a user can mute a change type globally, or mute a single competitor entirely (e.g. during a noisy redesign) with an optional auto-unmute date.
- **Digest:** weekly by default, configurable to daily or off, with a per-workspace send day and timezone.
- **Deduplication:** the same underlying change detected across two sources (a pricing change on the site *and* in a blog post) should collapse into one alert, not two.

## Classification Feedback
The LLM assigns change type and urgency, and nothing currently tunes that. This is the difference between a demo and something a team keeps paying for.

- Every finding carries thumbs-up / thumbs-down plus a correction: "this was `messaging`, not `feature_launch`" or "this is not urgent."
- Corrections are stored against the finding and against `(workspace_id, source_type, change_type)`.
- v1 use: corrected examples are fed back into the classification prompt as few-shot context for that workspace. No fine-tuning.
- Also surfaces "you've marked 8 of the last 10 hiring changes as noise — mute hiring for this competitor?" as a suggested rule.

## Source Health
A competitor can silently stop being monitored — a redesign breaks selectors, robots.txt tightens, a page starts returning 403 — and the dashboard looks identical to "nothing has changed." That failure mode quietly destroys trust in the product.

- Each Source tracks `last_attempt_at`, `last_success_at`, `consecutive_failures`, and a status: `healthy` / `degraded` / `failing` / `blocked`.
- `blocked` is distinct and means we are deliberately not crawling: robots.txt disallows it, or the site is returning sustained 403/429. It is never retried on the normal schedule.
- **Extraction drift** is a health signal too: if rule-based selectors stop matching and the LLM fallback starts carrying every crawl, the source is `degraded` even though fetches succeed.
- The dashboard shows a per-competitor health indicator, and a source that goes `failing` notifies the workspace — silence is never presented as "no changes."

## Change Timeline
Alerts are push and the battlecard is current-state; neither is browsable history. The timeline is the view people actually open.

- Per competitor: a reverse-chronological feed of all findings, baseline included.
- Filterable by change type, urgency, source, and date range; full-text searchable.
- Each entry links to the underlying diff and the raw snapshot that produced it, so a user can verify a claim rather than trusting the LLM's summary.
- A workspace-wide timeline across all competitors is the natural dashboard home.

## Cost Controls and Retention
LLM calls on every diff, on every source, on every competitor, plus RAG over the full history. Cost scales with customer count *and* with how chatty their competitors are — it needs bounds in the schema, not in a later panic.

- **Skip the LLM when it adds nothing:** diffs below a significance threshold (whitespace, reordering, rotating testimonials, copyright year, cache-busting query strings) are discarded before classification.
- **Per-workspace monthly budget** for LLM spend, with soft-warn and hard-stop thresholds. On hard stop, crawling and diffing continue, classification queues, and the workspace is told.
- **Crawl intervals are plan-bound**, not user-arbitrary — the main lever on cost.
- **Retention:** full-page snapshots are the expensive rows. Keep raw snapshots 30 days, then drop the raw payload and keep the extracted structured fields and diffs indefinitely. Findings, battlecards, and timeline entries are never auto-deleted.
- Keep the most recent snapshot per source regardless of age — it is the diff baseline.

## Billing
- Plans priced on tracked competitors and crawl frequency, the two things that actually drive cost.
- Free tier exists to make onboarding real: a small number of competitors, daily crawls, digest-only alerts.
- Paid tiers unlock more competitors, faster intervals, real-time channels, and Q&A/RAG.
- Stripe. Workspace-level subscription, owner-managed.

## Open Questions
- Authenticated pages: some pricing lives behind a login. Out of scope for v1, but it will be asked for.
- Per-competitor crawl intervals vs. a single workspace-wide interval — the former is more useful, the latter is much easier to schedule.
- Whether the weekly digest is per-user or per-workspace when members want different cadences.
## Stack
- Backend: Python / FastAPI, single service (auth, CRUD for competitors/sources/alerts, scraping, extraction, LLM classification, all in one)
- Frontend/dashboard: Next.js
- Database: Postgres (snapshots, structured findings, alerts)
- Job queue: Celery (or a simpler cron-based scheduler for v1) for crawl/diff jobs
- Scraping: Playwright (Python)
- LLM: classification, summarization, battlecard maintenance, Q&A

## Export
- Save findings/battlecards to a spreadsheet (Google Sheets)
- Save findings/battlecards to Google Docs