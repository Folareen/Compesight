"use server";

import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { Competitor } from "@/lib/types";

export async function createCompetitorAction(formData: FormData): Promise<void> {
  const name = formData.get("name");
  const websiteUrl = formData.get("website_url");
  if (typeof name !== "string" || name.trim() === "") {
    throw new Error("competitor name is required");
  }
  if (typeof websiteUrl !== "string" || websiteUrl.trim() === "") {
    throw new Error("website url is required");
  }

  const response = await apiFetch("/api/competitors", {
    method: "POST",
    body: JSON.stringify({ name: name.trim(), website_url: websiteUrl.trim() }),
  });
  const competitor = (await response.json()) as Competitor;

  redirect(`/competitors/${competitor.id}`);
}

export async function createSourceAction(competitorId: string, formData: FormData): Promise<void> {
  const url = formData.get("url");
  const type = formData.get("type");
  const crawlIntervalSeconds = formData.get("crawl_interval_seconds");
  if (typeof url !== "string" || url.trim() === "") {
    throw new Error("source url is required");
  }
  if (typeof type !== "string" || type.trim() === "") {
    throw new Error("source type is required");
  }
  const interval = typeof crawlIntervalSeconds === "string" ? parseInt(crawlIntervalSeconds, 10) : NaN;
  if (Number.isNaN(interval) || interval <= 0) {
    throw new Error("crawl interval must be a positive number of seconds");
  }

  await apiFetch(`/api/competitors/${competitorId}/sources`, {
    method: "POST",
    body: JSON.stringify({ url: url.trim(), type, crawl_interval_seconds: interval }),
  });

  redirect(`/competitors/${competitorId}`);
}

export async function triggerCrawlAction(sourceId: string, competitorId: string): Promise<void> {
  await apiFetch(`/api/sources/${sourceId}/crawl`, { method: "POST" });
  redirect(`/competitors/${competitorId}`);
}
