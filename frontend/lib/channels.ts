import { apiFetch } from "@/lib/api";
import type { ChannelConfigInput, NotificationChannel } from "@/lib/types";

export async function listChannels(): Promise<NotificationChannel[]> {
  const response = await apiFetch("/api/channels");
  return (await response.json()) as NotificationChannel[];
}

export async function createChannel(config: ChannelConfigInput): Promise<NotificationChannel> {
  const response = await apiFetch("/api/channels", {
    method: "POST",
    body: JSON.stringify({ config }),
  });
  return (await response.json()) as NotificationChannel;
}

export async function verifyChannel(id: string): Promise<NotificationChannel> {
  const response = await apiFetch(`/api/channels/${id}/verify`, { method: "POST" });
  return (await response.json()) as NotificationChannel;
}

export async function deleteChannel(id: string): Promise<void> {
  await apiFetch(`/api/channels/${id}`, { method: "DELETE" });
}
