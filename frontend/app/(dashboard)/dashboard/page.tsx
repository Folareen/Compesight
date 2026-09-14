import { EmptyState } from "@/components/EmptyState";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
      <EmptyState
        kind="pending"
        title="No competitors yet"
        description="Add a competitor to start tracking pricing, feature, and messaging changes."
      />
    </div>
  );
}
