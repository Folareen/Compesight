import { notFound } from "next/navigation";
import { DiffView } from "@/components/DiffView";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import { getFinding } from "@/lib/findings";

export default async function FindingDetailPage({
  params,
}: {
  params: Promise<{ id: string; findingId: string }>;
}) {
  const { findingId } = await params;
  const finding = await getFinding(findingId);
  if (finding === null) {
    notFound();
  }

  return (
    <div className="space-y-6">
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
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{finding.title}</h1>
        <p className="mt-1 text-sm text-muted">{finding.summary}</p>
      </div>
      <DiffView changeset={finding.changeset} snapshotId={finding.snapshot_id} />
    </div>
  );
}
