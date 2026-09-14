# Design System

Tailwind v4, configured in CSS at [`frontend/app/globals.css`](../frontend/app/globals.css) — there is no `tailwind.config.js`. Tokens are CSS variables exposed through `@theme inline`.

## Principle

This is a monitoring tool people check quickly, often daily, to answer "did anything happen?" Scanability beats decoration. Restraint with colour is what makes urgency legible — if everything is coloured, nothing reads as urgent.

## Tokens

Replace the scaffold's `:root` block. Light and dark both defined; dark is not an afterthought since dashboards get left open.

```css
@import "tailwindcss";

:root {
  --background: #ffffff;
  --surface: #f8fafc;
  --surface-raised: #ffffff;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;

  --foreground: #0f172a;
  --muted: #64748b;
  --faint: #94a3b8;

  --accent: #4f46e5;
  --accent-hover: #4338ca;
  --accent-fg: #ffffff;

  /* Urgency — the semantic core of the product */
  --urgency-high: #dc2626;
  --urgency-high-bg: #fef2f2;
  --urgency-medium: #d97706;
  --urgency-medium-bg: #fffbeb;
  --urgency-low: #64748b;
  --urgency-low-bg: #f8fafc;

  /* Source health */
  --health-healthy: #16a34a;
  --health-degraded: #d97706;
  --health-failing: #dc2626;
  --health-blocked: #64748b;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --surface: #111318;
    --surface-raised: #171a21;
    --border: #262b36;
    --border-strong: #363d4d;

    --foreground: #ededed;
    --muted: #9ba3b4;
    --faint: #6b7280;

    --accent: #6366f1;
    --accent-hover: #818cf8;

    --urgency-high: #f87171;
    --urgency-high-bg: #2a1416;
    --urgency-medium: #fbbf24;
    --urgency-medium-bg: #2a2010;
    --urgency-low: #9ba3b4;
    --urgency-low-bg: #171a21;

    --health-healthy: #4ade80;
    --health-degraded: #fbbf24;
    --health-failing: #f87171;
    --health-blocked: #6b7280;
  }
}

@theme inline {
  --color-background: var(--background);
  --color-surface: var(--surface);
  --color-surface-raised: var(--surface-raised);
  --color-border: var(--border);
  --color-foreground: var(--foreground);
  --color-muted: var(--muted);
  --color-faint: var(--faint);
  --color-accent: var(--accent);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}
```

**Never write a raw hex value in a component.** If a colour is missing, add a token.

Also fix the scaffold's `body { font-family: Arial, Helvetica, sans-serif }` — it overrides the Geist fonts the layout loads. Should be `var(--font-sans)`.

## Type

Geist Sans for UI, Geist Mono for prices, versions, diffs, and timestamps — anything where digits should align.

| Use | Class |
|---|---|
| Page title | `text-2xl font-semibold tracking-tight` |
| Section heading | `text-lg font-semibold` |
| Card title | `text-sm font-medium` |
| Body | `text-sm` |
| Meta / timestamp | `text-xs text-muted` |
| Numeric / diff | `font-mono text-sm` |

## Spacing and layout

4px base. Stick to `1 / 2 / 3 / 4 / 6 / 8 / 12 / 16`.

- Page gutter `px-6`, max content width `max-w-7xl`.
- Card padding `p-4`; card gap in a list `gap-3`.
- Radius: `rounded-lg` cards, `rounded-md` controls, `rounded-full` pills.
- Borders over shadows. One shadow level (`shadow-sm`) for genuinely raised things only.

## Components

Specs, not code — build them as real components in `frontend/components/` and reuse them.

### UrgencyBadge
`high` | `medium` | `low`. Pill, `text-xs font-medium px-2 py-0.5 rounded-full`, coloured text on its matching `-bg`. Never colour alone — always the word too, for colourblind users.

### HealthPill
`healthy` | `degraded` | `failing` | `blocked`. Dot + label. **`healthy` renders as a quiet dot with no label** — only problems earn attention. `blocked` is visually distinct from `failing`: it's a deliberate state, not an error.

### FindingCard
The workhorse — timeline and dashboard both. Layout:

```
[UrgencyBadge] [change-type] [competitor]        [relative time]
Title — one line, font-medium, truncates
Summary — two lines max, text-muted
[source icon + name]              [useful] [noise]
```

Whole card is a link to detail. Feedback buttons stop propagation. A `is_baseline` card shows a neutral "baseline" chip instead of an urgency badge.

### DiffView
Field-level, never raw HTML diff. One row per changed field: label, old value struck through in `--muted`, new value in `--foreground`, both `font-mono`. Always links to the source snapshot — verifiability is the point.

### BattlecardPanel
Sections: positioning, strengths, weaknesses, pricing tiers. Pricing tiers as a table, monospace figures. Each section shows when it last changed and links to the finding that changed it. An LLM-maintained doc must always show its provenance.

### EmptyState
Three distinct cases, never conflated:
- **Nothing yet** — baseline crawl still running. Show progress, not emptiness.
- **Nothing changed** — genuinely quiet. Reassuring, with last-checked time.
- **Can't check** — a source is failing. This is a *problem* state and must never look like "nothing changed". See [rules.md](rules.md): silence is never success.

## Accessibility

- Text contrast ≥ 4.5:1, borders/icons ≥ 3:1 — both themes.
- Colour is never the sole carrier of meaning.
- Visible focus rings. Don't remove outlines without replacing them.
- Time shows relative ("2h ago") with the absolute UTC timestamp in a `title`.
