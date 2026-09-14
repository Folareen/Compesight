import Link from "next/link";
import type { FieldChange } from "@/lib/types";

function formatValue(value: FieldChange["old_value"]): string {
  if (value === null) return "—";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

export function DiffView({ changeset, snapshotId }: { changeset: FieldChange[]; snapshotId: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface">
      {changeset.map((change) => (
        <div
          key={change.path}
          className="flex items-center justify-between gap-4 border-b border-border p-3 last:border-b-0"
        >
          <span className="text-sm text-muted">{change.path}</span>
          <span className="font-mono text-sm">
            <span className="text-muted line-through">{formatValue(change.old_value)}</span>
            {" → "}
            <span className="text-foreground">{formatValue(change.new_value)}</span>
          </span>
        </div>
      ))}
      <div className="p-3">
        <Link href={`/snapshots/${snapshotId}`} className="text-xs text-accent hover:underline">
          View source snapshot
        </Link>
      </div>
    </div>
  );
}
