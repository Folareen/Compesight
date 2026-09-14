import { apiFetch, ApiError } from "@/lib/api";
import type { Snapshot } from "@/lib/types";

export async function getSnapshot(id: string): Promise<Snapshot | null> {
  try {
    const response = await apiFetch(`/api/snapshots/${id}`);
    return (await response.json()) as Snapshot;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
