import { notFound } from "next/navigation";
import { getSnapshot } from "@/lib/snapshots";

export default async function SnapshotDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = await getSnapshot(id);
  if (snapshot === null) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Snapshot</h1>
        <p className="text-sm text-muted" title={snapshot.fetched_at}>
          Fetched {new Date(snapshot.fetched_at).toLocaleString()} — HTTP {snapshot.http_status ?? "—"}
        </p>
      </div>
      {snapshot.error ? (
        <p className="text-sm text-urgency-high">{snapshot.error}</p>
      ) : null}
      <pre className="max-h-[70vh] overflow-auto rounded-lg border border-border bg-surface p-4 font-mono text-xs whitespace-pre-wrap">
        {snapshot.raw_payload ?? "Raw payload not retained for this snapshot."}
      </pre>
    </div>
  );
}
