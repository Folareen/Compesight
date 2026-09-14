import Link from "next/link";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import type { Finding } from "@/lib/types";

export function FindingCard({ finding, competitorId }: { finding: Finding; competitorId: string }) {
  return (
    <Link
      href={`/competitors/${competitorId}/findings/${finding.id}`}
      className="block rounded-lg border border-border bg-surface p-4 hover:border-border-strong"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {finding.is_baseline ? (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full text-muted bg-surface-raised">
              Baseline
            </span>
          ) : (
            <UrgencyBadge urgency={finding.urgency} />
          )}
          <span className="text-xs text-muted">{finding.change_type}</span>
        </div>
        <span className="text-xs text-faint" title={finding.detected_at}>
          {new Date(finding.detected_at).toLocaleString()}
        </span>
      </div>
      <h3 className="mt-2 text-sm font-medium truncate">{finding.title}</h3>
      <p className="mt-1 text-sm text-muted line-clamp-2">{finding.summary}</p>
    </Link>
  );
}
