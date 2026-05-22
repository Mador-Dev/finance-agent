# Agents service

FastAPI host for **LangChain-first multi-agent** workflows (port **8090**).

## Packages

- `deepagents` — `create_deep_agent` coordinator + subagents (bootstrap, analysis)
- `langchain` — `create_agent` for web chat (`chat_agent/`)
- `langchain-openai` — model bindings

## Graphs

| Graph | Module | Role |
|-------|--------|------|
| Bootstrap | `bootstrap_agent/deep_agent.py` | Initial strategies per ticker (fundamentals, sentiment, risk, critic, optional bull/bear) |
| Analysis | `analysis_agent/deep_agent.py` | Deep-dive job execution |
| Chat | `chat_agent/agent.py` | Tool-calling advisor (portfolio, strategies, reports, job triggers) |

`langgraph.json` points LangGraph CLI at `build_bootstrap_deep_agent`.

## API

- `POST /api/bootstrap/start`
- `/api/jobs`, `/api/jobs/trigger` (header `X-User-Id`)
- `/api/chat/*`

## Persistence

Set `DATABASE_URL` (same Postgres as backend). `app/pg_store.py` writes portfolio, strategies, and report artifacts — no `users/` tree.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY, DATABASE_URL
uvicorn agents.main:app --host 0.0.0.0 --port 8090
```
