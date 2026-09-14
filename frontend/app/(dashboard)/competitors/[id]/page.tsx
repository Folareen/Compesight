import { Suspense } from "react";
import { notFound } from "next/navigation";
import { EmptyState } from "@/components/EmptyState";
import { FindingsTimelineClient } from "@/components/FindingsTimelineClient";
import { HealthPill } from "@/components/HealthPill";
import { getCompetitor, listSources } from "@/lib/competitors";
import { listFindings } from "@/lib/findings";
import { createSourceAction, triggerCrawlAction } from "../actions";

async function FindingsTimeline({ competitorId, sourceCount }: { competitorId: string; sourceCount: number }) {
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

  return (
    <FindingsTimelineClient
      competitorId={competitorId}
      initialFindings={findings}
      initialCursor={next_cursor}
      initialHasMore={has_more}
    />
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
          <FindingsTimeline competitorId={id} sourceCount={sources.length} />
        </Suspense>
      </section>
    </div>
  );
}
