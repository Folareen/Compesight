import { apiFetch, ApiError } from "@/lib/api";
import type { Finding, FindingListResponse } from "@/lib/types";

export async function listFindings(params: {
  competitorId?: string;
  cursor?: string;
}): Promise<FindingListResponse> {
  const query = new URLSearchParams();
  if (params.competitorId) query.set("competitor_id", params.competitorId);
  if (params.cursor) query.set("cursor", params.cursor);

  const response = await apiFetch(`/api/findings?${query.toString()}`);
  return (await response.json()) as FindingListResponse;
}

export async function getFinding(id: string): Promise<Finding | null> {
  try {
    const response = await apiFetch(`/api/findings/${id}`);
    return (await response.json()) as Finding;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
