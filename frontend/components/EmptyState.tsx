type EmptyStateProps =
  | { kind: "pending"; title: string; description: string }
  | { kind: "quiet"; title: string; description: string; lastCheckedAt: string }
  | { kind: "failing"; title: string; description: string };

export function EmptyState(props: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-border bg-surface px-6 py-12 text-center">
      {props.kind === "failing" ? (
        <span className="text-xs font-medium px-2 py-0.5 rounded-full text-urgency-high bg-urgency-high-bg">
          Problem
        </span>
      ) : null}
      <h2 className="text-sm font-medium">{props.title}</h2>
      <p className="max-w-sm text-sm text-muted">{props.description}</p>
      {props.kind === "quiet" ? (
        <p className="text-xs text-faint" title={props.lastCheckedAt}>
          Last checked {new Date(props.lastCheckedAt).toLocaleString()}
        </p>
      ) : null}
    </div>
  );
}
