# Portfolio Assistant

Private portfolio monitoring: holdings, strategies, reports, jobs, and alerts via web and Telegram/WhatsApp.

## Stack

| Layer | Path | Role |
|-------|------|------|
| Web | `frontend/` | Dashboard, onboarding, admin |
| API | `backend/` | Auth, jobs, reports, notifications (Express + Postgres) |
| Agents | `agents/` | LangChain / DeepAgents multi-agent service (FastAPI, port 8090) |

**All durable product state lives in Postgres** (`APP_DATABASE_URL`, schema in `db/application_postgres.sql`). There is no `users/` workspace for runtime data.

## Agents (`agents/`)

State-of-the-art **LangChain-first** multi-agent design:

- **Bootstrap & analysis** — `deepagents.create_deep_agent` with specialist subagents (fundamentals, sentiment, risk, critic, bull/bear) in `bootstrap_agent/` and `analysis_agent/`.
- **Web chat** — `langchain.agents.create_agent` tool-calling loop in `chat_agent/`.
- **Graph tooling** — `langgraph.json` registers the bootstrap graph for LangGraph CLI/dev.

When `DATABASE_URL` is set, the agents service reads/writes the same Postgres tables as the backend (portfolio, strategies, report artifacts).

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Product overview](docs/product/overview.md)

## Local run

1. Postgres + `APP_DATABASE_URL` in `backend/.env`
2. `cd backend && npm install && npm run dev`
3. `cd frontend && npm install && npm run dev`
4. `cd agents && pip install -r requirements.txt && uvicorn agents.main:app --port 8090`

Agent instructions for coding assistants: root `AGENTS.md`.
