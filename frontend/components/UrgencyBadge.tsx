import type { Urgency } from "@/lib/types";

const URGENCY_STYLES: Record<Urgency, { label: string; className: string }> = {
  high: { label: "High", className: "text-urgency-high bg-urgency-high-bg" },
  medium: { label: "Medium", className: "text-urgency-medium bg-urgency-medium-bg" },
  low: { label: "Low", className: "text-urgency-low bg-urgency-low-bg" },
};

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  const { label, className } = URGENCY_STYLES[urgency];
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${className}`}>{label}</span>
  );
}
