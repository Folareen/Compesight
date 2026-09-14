# Scraping and Extraction

The headline capability. Also the part most likely to break quietly, so the health signals in [data-model.md](data-model.md) are part of the feature, not instrumentation bolted on after.

## Being a good citizen

Not optional, and not merely ethical — a banned crawler IP breaks the product for every customer simultaneously.

- **Honour robots.txt.** Fetch and cache per host; re-check periodically. Disallowed → source becomes `blocked` with a reason shown to the user. There is no override flag, and nobody should add one.
- **Identify honestly.** A real User-Agent naming the product with a contact URL. Never impersonate a browser to evade detection.
- **Rate limit per host**, not per source — one competitor may have several tracked pages on one domain.
- **Exponential backoff with jitter** on failure. Honour `Retry-After` on 429/503.
- **Crawl at most once per interval**, and intervals are plan-bound. Nobody needs a competitor's homepage every 30 seconds.
- Sustained 403/429 is `blocked`, not `failing`. They're telling us to stop.

## Fetching

- **Playwright** for `website` and `pricing_page` — pricing is very often JS-rendered.
- **Plain HTTP** for feeds and JSON APIs. Don't pay for a browser you don't need.
- Wait for network idle plus the extraction selector, with a hard timeout. Never wait indefinitely.
- Block images, fonts, and media at the request level. We need the DOM, not the pixels — a large speed and bandwidth win.
- Store the *rendered* DOM, not the initial HTML response.
- Strip before hashing: session ids, CSRF tokens, cache-busting params, analytics payloads, timestamps. Otherwise `content_hash` differs on every fetch and the short-circuit never fires.

## Extraction

Selectors first, LLM fallback, always into a **fixed schema per source type** — free-form extraction can't be field-diffed, which is the whole point.

For pricing pages the schema is roughly: tier name, price (integer minor units + currency), billing period, feature list, whether highlighted.

- Per-source selector config lives in `source.config`, so a broken site can be fixed without a deploy.
- Record `method` (`selector` | `llm` | `mixed`) on every extraction.
- **Normalize before storing**: trim whitespace, collapse runs, parse prices into integers + currency, resolve relative URLs, sort unordered collections. Most spurious diffs are normalization failures, not real changes.

## Diffing

Structured fields only. Never diff raw HTML.

- Compare against the last **successful** extraction, not the last snapshot — a failed crawl must not read as "everything changed".
- Produce a field-level changeset: path, old value, new value.
- Run the significance filter (see [llm-usage.md](llm-usage.md)) before spending a model call.
- **Schema version changes are not findings.** When an extraction schema changes shape, re-baseline rather than reporting every field as changed.

## Extraction drift

The failure mode that matters most: fetches succeed, the page has been redesigned, and selectors silently return nothing or the wrong thing. HTTP-level health looks perfect.

Signals:
- selector match rate drops below its historical norm
- `method` shifts from `selector` to `llm` across consecutive crawls
- a previously populated required field goes empty
- an implausible change (every price changes at once, all tiers vanish)

Any of these → `degraded`, visible in the dashboard. An implausible change should be **held for review rather than alerted** — a false "they dropped all prices to $0" alert costs more trust than a slightly late true one.

## Failure handling

- Increment `consecutive_failures`; transition `healthy` → `degraded` → `failing`.
- `failing` notifies the workspace. Silence is never presented as "no changes" — see [rules.md](rules.md).
- `blocked` is terminal until cleared by a human or a much slower re-probe.
- Never let one bad source stall a queue or block others behind it.

## Idempotency

Assume every job runs at least twice — retries, redeploys, at-least-once delivery.

- Key snapshots on `(source_id, content_hash, fetch_window)`.
- Key findings on their changeset so a re-run updates rather than duplicates.
- Alert delivery checks for an existing `sent` alert before sending. Duplicate alerts are worse than late ones.
