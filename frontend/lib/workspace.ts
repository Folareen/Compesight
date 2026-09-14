import { apiFetch, ApiError } from "@/lib/api";
import type { Workspace } from "@/lib/types";

export async function getCurrentWorkspace(): Promise<Workspace | null> {
  try {
    const response = await apiFetch("/api/workspaces/current");
    return (await response.json()) as Workspace;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
