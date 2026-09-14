import type { SourceHealthStatus } from "@/lib/types";

const HEALTH_STYLES: Record<Exclude<SourceHealthStatus, "healthy">, { label: string; colorClass: string }> = {
  degraded: { label: "Degraded", colorClass: "bg-health-degraded" },
  failing: { label: "Failing", colorClass: "bg-health-failing" },
  blocked: { label: "Blocked", colorClass: "bg-health-blocked" },
};

export function HealthPill({ status }: { status: SourceHealthStatus }) {
  if (status === "healthy") {
    // Only problems earn attention — a quiet dot, no label.
    return <span className="inline-block h-2 w-2 rounded-full bg-health-healthy" title="Healthy" />;
  }

  const { label, colorClass } = HEALTH_STYLES[status];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <span className={`h-2 w-2 rounded-full ${colorClass}`} />
      {label}
    </span>
  );
}
