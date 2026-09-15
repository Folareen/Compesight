"use server";

import { revalidatePath } from "next/cache";
import { createChannel, deleteChannel, verifyChannel } from "@/lib/channels";
import { replaceRoutingRules } from "@/lib/routingRules";
import type { ChangeType, ChannelConfigInput, RoutingRule, RoutingRuleInput, Urgency } from "@/lib/types";

export async function createChannelAction(formData: FormData): Promise<void> {
  const kind = formData.get("kind");
  if (kind !== "email" && kind !== "slack" && kind !== "webhook") {
    throw new Error("channel kind is required");
  }

  let config: ChannelConfigInput;
  if (kind === "email") {
    const recipientEmail = formData.get("recipient_email");
    if (typeof recipientEmail !== "string" || recipientEmail.trim() === "") {
      throw new Error("recipient email is required");
    }
    config = { kind: "email", recipient_email: recipientEmail.trim() };
  } else if (kind === "slack") {
    const webhookUrl = formData.get("webhook_url");
    if (typeof webhookUrl !== "string" || webhookUrl.trim() === "") {
      throw new Error("slack webhook url is required");
    }
    config = { kind: "slack", webhook_url: webhookUrl.trim() };
  } else {
    const url = formData.get("url");
    if (typeof url !== "string" || url.trim() === "") {
      throw new Error("webhook url is required");
    }
    const secret = formData.get("secret");
    const trimmedSecret = typeof secret === "string" && secret.trim() !== "" ? secret.trim() : null;
    config = { kind: "webhook", url: url.trim(), secret: trimmedSecret };
  }

  await createChannel(config);
  revalidatePath("/settings/alerts");
}

export async function verifyChannelAction(channelId: string): Promise<void> {
  await verifyChannel(channelId);
  revalidatePath("/settings/alerts");
}

export async function deleteChannelAction(channelId: string): Promise<void> {
  await deleteChannel(channelId);
  revalidatePath("/settings/alerts");
}

export async function addRoutingRuleAction(existingRules: RoutingRuleInput[], formData: FormData): Promise<void> {
  const competitorId = formData.get("competitor_id");
  const changeType = formData.get("change_type");
  const minUrgency = formData.get("min_urgency");
  const channelIds = formData.getAll("channels");

  if (typeof minUrgency !== "string" || minUrgency.trim() === "") {
    throw new Error("minimum urgency is required");
  }
  if (channelIds.length === 0) {
    throw new Error("at least one channel is required");
  }

  const newRule: RoutingRuleInput = {
    competitor_id: typeof competitorId === "string" && competitorId !== "" ? competitorId : null,
    change_type: typeof changeType === "string" && changeType !== "" ? (changeType as ChangeType) : null,
    min_urgency: minUrgency as Urgency,
    channels: channelIds.map((id) => String(id)),
    enabled: true,
  };

  await replaceRoutingRules([...existingRules, newRule]);
  revalidatePath("/settings/alerts");
}

export async function removeRoutingRuleAction(existingRules: RoutingRule[], ruleId: string): Promise<void> {
  await replaceRoutingRules(
    existingRules.filter((rule) => rule.id !== ruleId).map((rule) => ({
      competitor_id: rule.competitor_id,
      change_type: rule.change_type,
      min_urgency: rule.min_urgency,
      channels: rule.channels,
      enabled: rule.enabled,
    })),
  );
  revalidatePath("/settings/alerts");
}
