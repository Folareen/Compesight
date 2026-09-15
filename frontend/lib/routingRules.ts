import { apiFetch } from "@/lib/api";
import type { RoutingRule, RoutingRuleInput } from "@/lib/types";

export async function listRoutingRules(): Promise<RoutingRule[]> {
  const response = await apiFetch("/api/routing-rules");
  const body = (await response.json()) as { rules: RoutingRule[] };
  return body.rules;
}

export async function replaceRoutingRules(rules: RoutingRuleInput[]): Promise<RoutingRule[]> {
  const response = await apiFetch("/api/routing-rules", {
    method: "PUT",
    body: JSON.stringify({ rules }),
  });
  const body = (await response.json()) as { rules: RoutingRule[] };
  return body.rules;
}
