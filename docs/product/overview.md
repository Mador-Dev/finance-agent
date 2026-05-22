# Product overview

Portfolio Assistant monitors holdings, maintains per-ticker **strategies**, runs scheduled **reports** (daily brief, full report, deep dive), and delivers **notifications** on web and messaging channels.

## Core flows

1. **Onboard** — register user, portfolio, persona, channels → `ACTIVE`
2. **Step-queue jobs** — analyst steps → synthesis → strategy row + report artifacts in Postgres
3. **Feed** — `report_batches` / `report_index` drive the dashboard feed
4. **Chat** — backend advisor (Postgres conversations); optional web chat via agents service

## Agents

Heavy LLM work runs in `agents/` using DeepAgents multi-agent graphs; results land in Postgres via the backend step queue or agents `DATABASE_URL` store.

## Terms

- **Report** — single analysis output (fundamentals, sentiment, quick check, …)
- **Strategy** — tracked thesis and verdict for a ticker
