import { createCompetitorAction } from "../actions";

export default function NewCompetitorPage() {
  return (
    <div className="mx-auto max-w-sm space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Add a competitor</h1>
      <form action={createCompetitorAction} className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="name">
            Name
          </label>
          <input
            id="name"
            name="name"
            required
            placeholder="Acme Inc."
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong focus-visible:ring-2 focus-visible:ring-accent"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="website_url">
            Website URL
          </label>
          <input
            id="website_url"
            name="website_url"
            type="url"
            required
            placeholder="https://acme.com"
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-border-strong focus-visible:ring-2 focus-visible:ring-accent"
          />
        </div>
        <button
          type="submit"
          className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-fg hover:bg-accent-hover"
        >
          Add competitor
        </button>
      </form>
    </div>
  );
}
