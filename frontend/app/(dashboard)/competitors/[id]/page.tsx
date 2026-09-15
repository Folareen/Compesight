import { Suspense } from "react";
import { notFound } from "next/navigation";
import { EmptyState } from "@/components/EmptyState";
import { FindingsTimelineClient } from "@/components/FindingsTimelineClient";
import { HealthPill } from "@/components/HealthPill";
import { getCompetitor, listSourceSuggestions, listSources } from "@/lib/competitors";
import { listFindings } from "@/lib/findings";
import { confirmSourceSuggestionAction, createSourceAction, triggerCrawlAction } from "../actions";

async function FindingsTimeline({
  competitorId,
  sourceCount,
  latestSuccessAt,
}: {
  competitorId: string;
  sourceCount: number;
  latestSuccessAt: string | null;
}) {
  const { data: findings, next_cursor, has_more } = await listFindings({ competitorId });

  if (sourceCount === 0) {
    return (
      <EmptyState
        kind="pending"
        title="No sources yet"
        description="Add a pricing page or website to start tracking changes."
      />
    );
  }

  if (findings.length === 0) {
    return (
      <EmptyState
        kind="pending"
        title="Waiting for the first crawl"
        description="This competitor's sources haven't been crawled yet — check back shortly."
      />
    );
  }

  const onlyBaseline = findings.every((f) => f.is_baseline);
  if (onlyBaseline && latestSuccessAt !== null) {
    return (
      <EmptyState
        kind="quiet"
        title="No changes yet"
        description="Baseline captured — this competitor's sources are being watched, nothing has changed since."
        lastCheckedAt={latestSuccessAt}
      />
    );
  }

  return (
    <FindingsTimelineClient
      competitorId={competitorId}
      initialFindings={findings}
      initialCursor={next_cursor}
      initialHasMore={has_more}
    />
  );
}

async function SourceSuggestions({
  competitorId,
  existingUrls,
}: {
  competitorId: string;
  existingUrls: Set<string>;
}) {
  const suggestions = await listSourceSuggestions(competitorId);
  const unadded = suggestions.filter((s) => !existingUrls.has(s.url));

  if (unadded.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-lg border border-dashed border-border bg-surface p-3">
      <p className="text-xs font-medium text-muted">Suggested sources</p>
      <ul className="space-y-2">
        {unadded.map((suggestion) => (
          <li key={suggestion.url} className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">{suggestion.type}</p>
              <p className="text-xs text-faint">{suggestion.url}</p>
            </div>
            <form
              action={confirmSourceSuggestionAction.bind(null, competitorId, suggestion.type, suggestion.url)}
            >
              <button
                type="submit"
                className="rounded-md border border-accent px-2 py-1 text-xs font-medium text-accent hover:bg-accent hover:text-accent-fg"
              >
                Add
              </button>
            </form>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function CompetitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const competitor = await getCompetitor(id);
  if (competitor === null) {
    notFound();
  }

  const sources = await listSources(id);
  const anySourceFailing = sources.some((s) => s.status === "failing" || s.status === "blocked");
  const successTimestamps = sources
    .map((s) => s.last_success_at)
    .filter((t): t is string => t !== null)
    .sort();
  const latestSuccessAt = successTimestamps.length > 0 ? successTimestamps[successTimestamps.length - 1] : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{competitor.name}</h1>
        <p className="text-sm text-muted">{competitor.website_url}</p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Sources</h2>
        {sources.length === 0 ? (
          <p className="text-sm text-muted">No sources yet.</p>
        ) : (
          <ul className="space-y-2">
            {sources.map((source) => (
              <li
                key={source.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface p-3"
              >
                <div>
                  <p className="text-sm font-medium">{source.type}</p>
                  <p className="text-xs text-faint">{source.url}</p>
                  {source.extraction_drift ? (
                    <p className="text-xs text-urgency-high">
                      Extraction drift — the page may have changed shape
                    </p>
                  ) : null}
                </div>
                <div className="flex items-center gap-3">
                  <HealthPill status={source.status} />
                  <form action={triggerCrawlAction.bind(null, source.id, competitor.id)}>
                    <button type="submit" className="text-xs text-accent hover:underline">
                      Crawl now
                    </button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}

        <Suspense fallback={null}>
          <SourceSuggestions competitorId={id} existingUrls={new Set(sources.map((s) => s.url))} />
        </Suspense>

        <form
          action={createSourceAction.bind(null, competitor.id)}
          className="flex flex-wrap items-end gap-2 rounded-lg border border-border bg-surface p-3"
        >
          <div className="space-y-1">
            <label className="text-xs font-medium" htmlFor="type">
              Type
            </label>
            <select
              id="type"
              name="type"
              className="rounded-md border border-border bg-surface-raised px-2 py-1.5 text-sm"
            >
              <option value="pricing_page">Pricing page</option>
              <option value="website">Website</option>
            </select>
          </div>
          <div className="flex-1 space-y-1">
            <label className="text-xs font-medium" htmlFor="url">
              URL
            </label>
            <input
              id="url"
              name="url"
              type="url"
              required
              placeholder="https://acme.com/pricing"
              className="w-full rounded-md border border-border bg-surface-raised px-2 py-1.5 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium" htmlFor="crawl_interval_seconds">
              Interval (s)
            </label>
            <input
              id="crawl_interval_seconds"
              name="crawl_interval_seconds"
              type="number"
              defaultValue={3600}
              min={60}
              required
              className="w-28 rounded-md border border-border bg-surface-raised px-2 py-1.5 text-sm"
            />
          </div>
          <button
            type="submit"
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:bg-accent-hover"
          >
            Add source
          </button>
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Change timeline</h2>
        {anySourceFailing ? (
          <EmptyState
            kind="failing"
            title="A source can't be checked"
            description="One of this competitor's sources is failing or blocked — findings may be incomplete until it recovers."
          />
        ) : null}
        <Suspense fallback={<p className="text-sm text-muted">Loading findings…</p>}>
          <FindingsTimeline competitorId={id} sourceCount={sources.length} latestSuccessAt={latestSuccessAt} />
        </Suspense>
      </section>
    </div>
  );
}
