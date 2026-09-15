import { listChannels } from "@/lib/channels";
import { listCompetitors } from "@/lib/competitors";
import { listRoutingRules } from "@/lib/routingRules";
import {
  addRoutingRuleAction,
  createChannelAction,
  deleteChannelAction,
  removeRoutingRuleAction,
  verifyChannelAction,
} from "./actions";

const CHANGE_TYPES = [
  "pricing",
  "feature_launch",
  "messaging",
  "hiring",
  "funding",
  "partnership",
  "content",
  "other",
] as const;

export default async function AlertsSettingsPage() {
  const [channels, rules, competitors] = await Promise.all([
    listChannels(),
    listRoutingRules(),
    listCompetitors(),
  ]);

  const ruleInputs = rules.map((rule) => ({
    competitor_id: rule.competitor_id,
    change_type: rule.change_type,
    min_urgency: rule.min_urgency,
    channels: rule.channels,
    enabled: rule.enabled,
  }));

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>

      <section className="space-y-4">
        <h2 className="text-lg font-medium">Notification channels</h2>

        {channels.length === 0 ? (
          <p className="text-sm text-muted">No channels yet — add one below.</p>
        ) : (
          <ul className="space-y-2">
            {channels.map((channel) => (
              <li
                key={channel.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface p-3"
              >
                <div>
                  <span className="text-sm font-medium">{channel.kind}</span>
                  <span className="ml-2 text-sm text-muted">{channel.display_identifier}</span>
                  {channel.verified_at === null && (
                    <span className="ml-2 text-xs text-amber-600">unverified</span>
                  )}
                </div>
                <div className="flex gap-2">
                  {channel.verified_at === null && (
                    <form action={verifyChannelAction.bind(null, channel.id)}>
                      <button type="submit" className="text-xs font-medium text-accent hover:underline">
                        Verify
                      </button>
                    </form>
                  )}
                  <form action={deleteChannelAction.bind(null, channel.id)}>
                    <button type="submit" className="text-xs font-medium text-red-600 hover:underline">
                      Remove
                    </button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}

        <form action={createChannelAction} className="space-y-3 rounded-lg border border-border bg-surface p-4">
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="kind">
              Channel type
            </label>
            <select
              id="kind"
              name="kind"
              defaultValue="slack"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            >
              <option value="slack">Slack (incoming webhook)</option>
              <option value="email">Email</option>
              <option value="webhook">Generic webhook</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="recipient_email">
              Email recipient (for Email channels)
            </label>
            <input
              id="recipient_email"
              name="recipient_email"
              type="email"
              placeholder="team@example.com"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="webhook_url">
              Slack webhook URL (for Slack channels)
            </label>
            <input
              id="webhook_url"
              name="webhook_url"
              type="url"
              placeholder="https://hooks.slack.com/services/…"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="url">
              Webhook URL (for generic Webhook channels)
            </label>
            <input
              id="url"
              name="url"
              type="url"
              placeholder="https://example.com/hooks/compesight"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="secret">
              Webhook secret (optional, generic webhook only)
            </label>
            <input
              id="secret"
              name="secret"
              type="text"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            />
          </div>
          <button
            type="submit"
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:bg-accent-hover"
          >
            Add channel
          </button>
        </form>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-medium">Routing rules</h2>
        <p className="text-sm text-muted">
          Most specific rule wins: competitor + type, then competitor, then workspace + type, then the workspace
          default.
        </p>

        {rules.length === 0 ? (
          <p className="text-sm text-muted">No routing rules yet — nothing will alert until you add one.</p>
        ) : (
          <ul className="space-y-2">
            {rules.map((rule) => (
              <li
                key={rule.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface p-3"
              >
                <span className="text-sm">
                  {rule.competitor_id
                    ? competitors.find((c) => c.id === rule.competitor_id)?.name ?? "Unknown competitor"
                    : "All competitors"}{" "}
                  · {rule.change_type ?? "all change types"} · min urgency {rule.min_urgency} ·{" "}
                  {rule.channels.length} channel(s)
                </span>
                <form action={removeRoutingRuleAction.bind(null, rules, rule.id)}>
                  <button type="submit" className="text-xs font-medium text-red-600 hover:underline">
                    Remove
                  </button>
                </form>
              </li>
            ))}
          </ul>
        )}

        <form
          action={addRoutingRuleAction.bind(null, ruleInputs)}
          className="space-y-3 rounded-lg border border-border bg-surface p-4"
        >
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="competitor_id">
              Competitor (leave blank for workspace default)
            </label>
            <select
              id="competitor_id"
              name="competitor_id"
              defaultValue=""
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            >
              <option value="">All competitors</option>
              {competitors.map((competitor) => (
                <option key={competitor.id} value={competitor.id}>
                  {competitor.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="change_type">
              Change type (leave blank for all)
            </label>
            <select
              id="change_type"
              name="change_type"
              defaultValue=""
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            >
              <option value="">All change types</option>
              {CHANGE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="min_urgency">
              Minimum urgency
            </label>
            <select
              id="min_urgency"
              name="min_urgency"
              defaultValue="medium"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </div>
          <div className="space-y-1">
            <span className="text-sm font-medium">Channels</span>
            <div className="space-y-1">
              {channels.length === 0 ? (
                <p className="text-xs text-muted">Add a channel above first.</p>
              ) : (
                channels.map((channel) => (
                  <label key={channel.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" name="channels" value={channel.id} />
                    {channel.kind} — {channel.display_identifier}
                  </label>
                ))
              )}
            </div>
          </div>
          <button
            type="submit"
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:bg-accent-hover"
          >
            Add rule
          </button>
        </form>
      </section>
    </div>
  );
}
