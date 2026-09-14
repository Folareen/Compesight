import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";
import { listCompetitors } from "@/lib/competitors";

export default async function CompetitorsPage() {
  const competitors = await listCompetitors();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Competitors</h1>
        <Link
          href="/competitors/new"
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:bg-accent-hover"
        >
          Add competitor
        </Link>
      </div>

      {competitors.length === 0 ? (
        <EmptyState
          kind="pending"
          title="No competitors yet"
          description="Add a competitor to start tracking pricing, feature, and messaging changes."
        />
      ) : (
        <ul className="space-y-3">
          {competitors.map((competitor) => (
            <li key={competitor.id}>
              <Link
                href={`/competitors/${competitor.id}`}
                className="block rounded-lg border border-border bg-surface p-4 hover:border-border-strong"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{competitor.name}</span>
                  <span className="text-xs text-muted">{competitor.status}</span>
                </div>
                <p className="mt-1 text-xs text-faint">{competitor.website_url}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
