# Portfolio Assistant

A private-investor portfolio operations product that keeps holdings continuously monitored, escalates changed positions, and delivers concise updates through Telegram or web.

## Start here

- Product overview: [`docs/product/overview.md`](docs/product/overview.md)
- GSD planning docs: [`docs/gsd-docs/`](docs/gsd-docs/)
- Pilot feature catalog: [`docs/pilot-features/`](docs/pilot-features/)
- Historical production reports: [`docs/archive/production-reports/`](docs/archive/production-reports/)
- Historical bug notes: [`docs/archive/open-bugs/`](docs/archive/open-bugs/)

## Active surfaces

- `backend/` — API, scheduling, jobs, notifications, observability, database integration.
- `frontend/` — dashboard and user-facing web app.
- `shared/user-workspace/` — runtime template files copied into per-user workspaces.
- `data/` — runtime configuration used by the backend and deploy process.
- `scripts/` — repository verification scripts.

Development-agent instructions intentionally remain in root `AGENTS.md` because local model harnesses load it by convention.
