# AGENTS.md — System agent rules

## Scope

Portfolio Assistant product: `backend/`, `frontend/`, `agents/`, `db/`, `docs/`, `shared/`, `data/`.

You are the **system agent** (product/infra/admin), not a per-user finance advisor.

## Persistence

- **Postgres is the only source of truth** for users, portfolio, strategies, jobs, report artifacts, persona text, notifications, control, and chat (backend).
- Do not add new reads/writes under `users/`; extend `db/application_postgres.sql` and the `*Store.ts` services first.
- `agents/` must use LangChain / DeepAgents patterns already in tree; prefer coordinator + subagent graphs over monolithic prompts.

## Write boundaries

Allowed: paths above, root `*.md`.

Avoid bulk edits to production user rows; fix product code instead.

## Startup

1. Read relevant backend/frontend/agents code.
2. Reconcile `APP_DATABASE_URL`, env, and `data/` system config.
3. Touch DB user rows only for targeted maintenance.

## Product terms

- **Report** — one analysis event on an asset.
- **Strategy** — long-lived thesis for an asset (`strategies` table).

## Success

Change works, matches Postgres-first direction, low regression risk, clearer observability when behavior was opaque.
