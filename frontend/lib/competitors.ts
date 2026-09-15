import { apiFetch, ApiError } from "@/lib/api";
import type { Competitor, Source, SourceSuggestion } from "@/lib/types";

export async function listCompetitors(): Promise<Competitor[]> {
  const response = await apiFetch("/api/competitors");
  return (await response.json()) as Competitor[];
}

export async function getCompetitor(id: string): Promise<Competitor | null> {
  try {
    const response = await apiFetch(`/api/competitors/${id}`);
    return (await response.json()) as Competitor;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function listSources(competitorId: string): Promise<Source[]> {
  const response = await apiFetch(`/api/competitors/${competitorId}/sources`);
  return (await response.json()) as Source[];
}

export async function listSourceSuggestions(competitorId: string): Promise<SourceSuggestion[]> {
  const response = await apiFetch(`/api/competitors/${competitorId}/source-suggestions`);
  return (await response.json()) as SourceSuggestion[];
}
