import { redirect } from "next/navigation";
import { NavBar } from "@/components/NavBar";
import { getCurrentWorkspace } from "@/lib/workspace";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const workspace = await getCurrentWorkspace();
  if (workspace === null) {
    redirect("/onboarding");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <NavBar workspaceName={workspace.name} />
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
    </div>
  );
}
