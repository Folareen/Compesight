# Compesight — Spec

## What it is
A web app that monitors competitors' websites and public online presence, detects changes, classifies them with an LLM, and surfaces them as alerts and a running battlecard per competitor.

## Format
Full web app with a dashboard. Not a bare API service.

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