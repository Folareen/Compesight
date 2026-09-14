import { redirect } from "next/navigation";
import { getCurrentWorkspace } from "@/lib/workspace";
import { createWorkspaceAction } from "./actions";

export default async function OnboardingPage() {
  const workspace = await getCurrentWorkspace();
  if (workspace !== null) {
    redirect("/dashboard");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <form action={createWorkspaceAction} className="w-full max-w-sm space-y-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Name your workspace</h1>
          <p className="text-sm text-muted">You can invite teammates later.</p>
        </div>
        <input
          name="name"
          required
          placeholder="Acme Inc."
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong focus-visible:ring-2 focus-visible:ring-accent"
        />
        <button
          type="submit"
          className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-fg hover:bg-accent-hover"
        >
          Create workspace
        </button>
      </form>
    </div>
  );
}
