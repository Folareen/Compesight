export type Workspace = {
  id: string;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
};

export type CompetitorStatus = "pending" | "active" | "muted";

export type Competitor = {
  id: string;
  name: string;
  website_url: string;
  status: CompetitorStatus;
  muted_until: string | null;
  created_at: string;
};

export type SourceType =
  | "website"
  | "pricing_page"
  | "rss"
  | "reddit"
  | "hackernews"
  | "producthunt"
  | "youtube"
  | "github"
  | "appstore"
  | "playstore";

export type SourceHealthStatus = "healthy" | "degraded" | "failing" | "blocked";

export type Source = {
  id: string;
  competitor_id: string;
  type: SourceType;
  url: string;
  crawl_interval_seconds: number;
  status: SourceHealthStatus;
  last_attempt_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
  blocked_reason: string | null;
  extraction_failure_streak: number;
  extraction_drift: boolean;
};

export type SourceSuggestion = {
  type: SourceType;
  url: string;
};

export type ChangeType =
  | "pricing"
  | "feature_launch"
  | "messaging"
  | "hiring"
  | "funding"
  | "partnership"
  | "content"
  | "other";

export type Urgency = "high" | "medium" | "low";

export type FieldChange = {
  path: string;
  old_value: string | number | boolean | string[] | null;
  new_value: string | number | boolean | string[] | null;
};

// Discriminated on is_baseline: a baseline finding carries no urgency, a
// real change always does — never both, never neither (docs/frontend-rules.md).
export type Finding =
  | {
      id: string;
      competitor_id: string;
      source_id: string;
      snapshot_id: string;
      is_baseline: true;
      change_type: ChangeType;
      title: string;
      summary: string;
      changeset: FieldChange[];
      detected_at: string;
    }
  | {
      id: string;
      competitor_id: string;
      source_id: string;
      snapshot_id: string;
      is_baseline: false;
      change_type: ChangeType;
      urgency: Urgency;
      title: string;
      summary: string;
      changeset: FieldChange[];
      detected_at: string;
    };

export type FindingListResponse = {
  data: Finding[];
  next_cursor: string | null;
  has_more: boolean;
};

export type ChannelKind = "email" | "slack" | "webhook";

export type NotificationChannel = {
  id: string;
  kind: ChannelKind;
  display_identifier: string;
  verified_at: string | null;
  created_at: string;
};

export type EmailChannelConfigInput = { kind: "email"; recipient_email: string };
export type SlackChannelConfigInput = { kind: "slack"; webhook_url: string };
export type WebhookChannelConfigInput = { kind: "webhook"; url: string; secret: string | null };

export type ChannelConfigInput =
  | EmailChannelConfigInput
  | SlackChannelConfigInput
  | WebhookChannelConfigInput;

export type RoutingRule = {
  id: string;
  competitor_id: string | null;
  change_type: ChangeType | null;
  min_urgency: Urgency;
  channels: string[];
  enabled: boolean;
};

export type RoutingRuleInput = {
  competitor_id: string | null;
  change_type: ChangeType | null;
  min_urgency: Urgency;
  channels: string[];
  enabled: boolean;
};

export type Snapshot = {
  id: string;
  source_id: string;
  fetched_at: string;
  content_hash: string;
  raw_payload: string | null;
  http_status: number | null;
  error: string | null;
};
