# Slice Execution Map

Implement slices in dependency order. Do not skip S01; it establishes the inventory and safety gates that make later destructive cutovers safe.

## S01 — State ownership inventory and migration safety gates

Risk: high  
Depends on: none

Purpose: produce a current inventory of remaining filesystem-owned state, classify retained filesystem paths, strengthen parity verification, and fix known path mismatches before any destructive cutover.

Likely work:

- migration scripts;
- parity verifier;
- static/path guard tests;
- documentation of state ownership;
- known notification path mismatch fix.

DB expectation: no major schema change. Strengthen verification around existing users, strategies, report batches/index, notifications outbox, escalation history, and migration archive.

Completion proof:

- inventory exists and is discoverable;
- every touched path has an ownership category;
- guard/parity tests fail on accidental live reads/writes to retired domains;
- downstream slices know what they can safely consume.

## S02 — Retire filesystem job lifecycle

Risk: high  
Depends on: S01

Purpose: move user/admin job lifecycle reads and writes to Postgres-owned job/work-item state.

Likely work:

- job service;
- job/admin routes;
- trigger flow;
- supersession tooling;
- watchdog/reconciliation tests;
- archive or delete `users/<id>/data/jobs/*.json` as live state.

DB expectation: use existing jobs, ticker work items, step work items, and lifecycle events. Add columns only if implementation proves a real gap.

Completion proof:

- job list/detail/supersession/watchdog/trigger flows operate without live job JSON;
- parity with representative legacy job files is verified;
- legacy job JSON is archive-only or absent.

## S03 — Retire auth.json and token-version filesystem state

Risk: high  
Depends on: S01

Purpose: make authentication, token-version, and forced logout state DB-owned.

Likely work:

- auth middleware/routes;
- onboarding registration;
- password change/login flows;
- token-version control logic;
- auth tests;
- archive `users/<id>/auth.json` after parity.

DB expectation: use existing users password hash and token version fields. No expected schema change.

Completion proof:

- login, registration, password changes, JWT validation, and force logout work after `auth.json` is absent;
- no secret material is printed by migration/parity tooling;
- lockout rollback path is documented.

## S04 — Retire profile.json and user data/config.json

Risk: medium  
Depends on: S03

Purpose: move user profile/config product state to Postgres.

Likely work:

- profile service;
- onboarding;
- admin user settings;
- job admission;
- model-tier/profile logic;
- archive profile/config JSON as canonical state.

DB expectation: use existing display name, schedule, rate limits, model tier, and model profile fields. Possibly add plan/user-plan state only if current live JSON has product-critical state not represented.

Completion proof:

- user display name, schedule, rate limits, plan/model tier/profile selection, and related surfaces work without profile/config JSON;
- new writes go to Postgres;
- legacy files are import/parity/archive only.

## S05 — Retire system and user control JSON

Risk: medium  
Depends on: S03

Purpose: move global and per-user control state to DB-owned structures.

Likely work:

- control service;
- admin routes;
- restriction middleware/logic;
- archive root system-control and per-user control JSON.

DB expectation: add system control and user control tables because current user restriction fields are too narrow.

Completion proof:

- system lock/broadcast state, user restrictions/banners/expiry, and token-version force logout are DB-owned;
- behavior works without root and per-user control JSON;
- admin/audit visibility remains intact.

## S06 — Retire support-messages.json

Risk: low  
Depends on: S01

Purpose: move support submissions and admin review state to Postgres.

Likely work:

- support service;
- support/admin routes;
- tests;
- archive root support-messages JSON.

DB expectation: add support messages table with status, user, and time indexes.

Completion proof:

- support submissions, admin listing, and status updates work without support-messages JSON;
- migration is idempotent and dry-run by default.

## S07 — Retire notification JSON outbox and feed event ambiguity

Risk: medium  
Depends on: S01, S04

Purpose: make notifications DB-owned and resolve whether feed events are product-visible state or derived artifacts.

Likely work:

- notification service;
- notification routes;
- feed service;
- migration/parity tests;
- archive notification JSON.

DB expectation: use existing notifications outbox. Possibly add notification preferences or feed events if current feed events are confirmed product-visible state.

Completion proof:

- notification listing, unread counts, delivery updates, mark-read, and publish dedupe use DB state;
- legacy notification JSON is archive-only;
- feed event ownership is explicitly decided.

## S08 — Retire report index JSON and decide report artifact ownership

Risk: high  
Depends on: S02, S07

Purpose: make report feed/index routes DB-owned and decide report-detail artifact ownership.

Likely work:

- report routes;
- feed service;
- full report service;
- report index store;
- rebuild/migration scripts;
- retire local report index JSON.

DB expectation: use existing report batches and report index. Decide whether report detail artifacts become DB JSONB rows or DB metadata plus artifact/object storage.

Completion proof:

- report feed/index routes use DB source of truth;
- report detail reads have one explicit ownership model;
- no accidental local canonical index files remain.

## S09 — Retire strategy JSON as canonical state

Risk: medium  
Depends on: S08

Purpose: make strategies table canonical for strategy state and demote strategy JSON to export/artifact if retained.

Likely work:

- strategy file service;
- strategy store;
- quick/full/deep/report services;
- retire ticker strategy JSON as canonical state.

DB expectation: use existing strategies table. Add fields only if current live JSON has product-critical data not represented.

Completion proof:

- quick check, daily/full/deep-dive, report views, and strategy exports use DB state;
- strategy JSON is absent, derived, or export-only;
- parity checks cover representative strategies.

## S10 — Retire state.json for lifecycle and onboarding state

Risk: high  
Depends on: S03, S04, S09

Purpose: move lifecycle/onboarding/bootstrap/progress state to typed DB structures.

Likely work:

- state service;
- onboarding routes;
- scheduler eligibility;
- bootstrap/progress logic;
- archive root state JSON.

DB expectation: add user lifecycle/onboarding state table or equivalent typed structure for onboarding, bootstrap, pending deep dives, timestamps, and transition metadata.

Completion proof:

- onboarding, bootstrap progress, active-user eligibility, pending deep dives, report timestamps, and state transitions work without state JSON;
- transitions are observable and recoverable.

## S11 — Retire portfolio.json as canonical holdings

Risk: high  
Depends on: S10

Purpose: make holdings derive from DB ledger/portfolio state.

Likely work:

- portfolio routes;
- portfolio risk service;
- strategy baseline service;
- ledger replay/import scripts;
- demote or archive portfolio JSON.

DB expectation: use existing position transactions and corporate actions. Possibly add portfolio accounts if account identity needs normalization beyond free text.

Completion proof:

- portfolio API, risk snapshots, strategy baseline inputs, and active-user eligibility derive holdings from DB state;
- legacy portfolio JSON fixtures match replayed holdings before demotion;
- ledger replay/import remains idempotent.

## S12 — Stop provisioning retired product-state files and document deploy-anywhere blockers

Risk: medium  
Depends on: S02, S03, S04, S05, S06, S07, S08, S09, S10, S11

Purpose: prevent new user workspaces from recreating retired DB-owned state files and document remaining deploy-anywhere blockers.

Likely work:

- workspace service;
- shared user workspace templates;
- docs/tests;
- final remaining-state map.

DB expectation: no primary schema change.

Completion proof:

- new user workspaces contain only legitimate workspace/prompt/artifact scaffolding;
- no retired DB-owned JSON state is provisioned;
- final blocker map identifies remaining work for backups, environments, GitOps, artifact storage, service splitting, and portable deployment.
