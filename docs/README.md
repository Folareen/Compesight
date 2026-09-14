# Compesight Docs

Reference material for building Compesight. [`../spec.md`](../spec.md) is the product spec — *what* we are building and why. These docs cover *how*.

## Read this first

| Doc | Read it when |
|---|---|
| [rules.md](rules.md) | **Always.** Universal non-negotiables. Read before writing any code. |
| [backend-rules.md](backend-rules.md) | Working in `backend/` — FastAPI, Python, jobs, database |
| [frontend-rules.md](frontend-rules.md) | Working in `frontend/` — Next.js 16, React, styling |
| [architecture.md](architecture.md) | Touching services, data flow, or the job pipeline |
| [data-model.md](data-model.md) | Adding or changing any table |
| [api-conventions.md](api-conventions.md) | Adding or changing an endpoint |
| [design-system.md](design-system.md) | Building any UI |
| [build-plan.md](build-plan.md) | Deciding what to work on next |
| [llm-usage.md](llm-usage.md) | Writing anything that calls a model |
| [scraping.md](scraping.md) | Working on crawl, extraction, or diffing |

## Doc rules

- Both rules files carry a **Code simplicity** section: validate at the boundary, trust typed code past it. Read it before a refactor — it says what to *keep* as well as what to remove.
- These docs describe **intended** design. Where a doc and the code disagree, the code is the truth and the doc is a bug — fix the doc in the same change.
- Decisions with a trade-off record *why*, so they can be revisited on purpose rather than reversed by accident.
- Don't duplicate the spec here. Link to it.
