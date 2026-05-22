# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? | Made By |
|---|------|-------|----------|--------|-----------|------------|---------|
| D001 | Next DB/backend migration milestone planning | architecture | How to handle remaining filesystem-backed production state during cleanup | Retire filesystem ownership domain-by-domain rather than preserving legacy-compatible facades; temporary bridges are allowed only for import/parity and must be removed or guarded. | The cleanup goal is backend/Postgres-owned product state that can support portable deployments, backups, multiple environments, and service splitting. Investing in better legacy filesystem services would keep deprecated OpenClaw-era assumptions alive. | Yes, for artifact storage strategy only; product-state ownership remains DB/backend. | human |
