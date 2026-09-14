import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

export function NavBar({ workspaceName }: { workspaceName: string }) {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-sm font-semibold tracking-tight">
            Compesight
          </Link>
          <span className="text-sm text-muted">{workspaceName}</span>
        </div>
        <UserButton />
      </div>
    </header>
  );
}
