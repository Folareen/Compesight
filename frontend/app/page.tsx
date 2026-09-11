"use client";

import { useEffect, useState } from "react";

type Status = "loading" | "online" | "offline";

export default function Home() {
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${apiUrl}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error("Bad response");
        return res.json();
      })
      .then((data) => setStatus(data.status === "ok" ? "online" : "offline"))
      .catch(() => setStatus("offline"));
  }, []);

  const statusConfig: Record<Status, { label: string; color: string }> = {
    loading: { label: "Checking…", color: "bg-zinc-400" },
    online: { label: "Backend connected", color: "bg-green-500" },
    offline: { label: "Backend unreachable", color: "bg-red-500" },
  };

  const { label, color } = statusConfig[status];

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-col items-center gap-6 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Compesight
        </h1>
        <p className="max-w-md text-zinc-600 dark:text-zinc-400">
          Competitor monitoring, from crawl to battlecard.
        </p>
        <div className="flex items-center gap-2 rounded-full border border-black/8 px-4 py-2 text-sm font-medium text-zinc-700 dark:border-white/[.145] dark:text-zinc-300">
          <span className={`h-2 w-2 rounded-full ${color}`} />
          {label}
        </div>
      </main>
    </div>
  );
}
