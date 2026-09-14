"use server";

import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";

export async function createWorkspaceAction(formData: FormData): Promise<void> {
  const name = formData.get("name");
  if (typeof name !== "string" || name.trim() === "") {
    throw new Error("workspace name is required");
  }

  await apiFetch("/api/workspaces/bootstrap", {
    method: "POST",
    body: JSON.stringify({ name: name.trim() }),
  });

  redirect("/dashboard");
}
