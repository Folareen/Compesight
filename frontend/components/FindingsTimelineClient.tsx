"use client";

import { useState } from "react";
import { FindingCard } from "@/components/FindingCard";
import type { Finding, FindingListResponse } from "@/lib/types";

export function FindingsTimelineClient({
  competitorId,
  initialFindings,
  initialCursor,
  initialHasMore,
}: {
  competitorId: string;
  initialFindings: Finding[];
  initialCursor: string | null;
  initialHasMore: boolean;
}) {
  const [findings, setFindings] = useState(initialFindings);
  const [cursor, setCursor] = useState(initialCursor);
  const [hasMore, setHasMore] = useState(initialHasMore);
  const [loading, setLoading] = useState(false);

  async function loadMore() {
    if (cursor === null) return;
    setLoading(true);
    try {
      const query = new URLSearchParams({ competitor_id: competitorId, cursor });
      const response = await fetch(`/api/findings?${query.toString()}`);
      const page = (await response.json()) as FindingListResponse;
      setFindings((prev) => [...prev, ...page.data]);
      setCursor(page.next_cursor);
      setHasMore(page.has_more);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <ul className="space-y-3">
        {findings.map((finding) => (
          <li key={finding.id}>
            <FindingCard finding={finding} competitorId={competitorId} />
          </li>
        ))}
      </ul>
      {hasMore ? (
        <button
          type="button"
          onClick={loadMore}
          disabled={loading}
          className="text-sm text-accent hover:underline disabled:opacity-50"
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      ) : null}
    </div>
  );
}
