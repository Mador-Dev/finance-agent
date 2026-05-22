# M001: Postgres-Owned Product State Migration

**Vision:** Continue the cleanup phase by retiring OpenClaw-era and VPS-local filesystem ownership of production application state. By the end of this milestone, core user, job, control, notification, report-index, strategy, onboarding, and portfolio state should be backend/Postgres-owned, with filesystem use explicitly limited to user prompts, derived artifacts, cold archives, and disposable caches. This is the foundation for deploy-anywhere infrastructure: managed backups, multiple environments, GitOps-compatible rollout, and eventual service splitting.

## Success Criteria

- Every migrated domain has an explicit source-of-truth declaration: Postgres product state, derived artifact, prompt/workspace file, cold archive, or disposable cache.
- Live backend reads/writes for completed domains use Postgres, not `users/*` or root `data/*` JSON files.
- Temporary filesystem bridges exist only for migration/parity and have deletion guards or explicit follow-up removal points.
- Migration scripts are idempotent, dry-run by default, do not print secrets, and archive destructive legacy inputs to `migration_archive`.
- New users are not provisioned with JSON files for domains already retired to Postgres.
- The milestone produces a remaining-state map identifying what still blocks deploy-anywhere infrastructure, backups, multiple environments, GitOps, and future service splitting.

## Slices

- [ ] **S01: State ownership inventory and migration safety gates** `risk:high` `depends:[]`
  > After this: A migration-state inventory and parity/guard test suite identifies every remaining `users/*` and root `data/*` production-state path, classifies retained filesystem paths, and fixes known parity gaps before destructive cutovers.

- [ ] **S02: Retire filesystem job lifecycle** `risk:high` `depends:[S01]`
  > After this: User/admin job listing, job detail, supersession, watchdog/reconciliation, and job-trigger flows operate from Postgres `jobs`/work-item tables with no live dependency on `users/<id>/data/jobs/*.json`.

- [ ] **S03: Retire auth.json and token-version filesystem state** `risk:high` `depends:[S01]`
  > After this: Login, registration, password changes, JWT validation, and force-logout/token-version checks use the `users` table and continue working after `auth.json` is absent.

- [ ] **S04: Retire profile.json and user config.json** `risk:medium` `depends:[S03]`
  > After this: User display name, schedule, rate limits, plan/model tier/profile selection, and related admin/user surfaces operate from Postgres even when `profile.json` and `data/config.json` are absent.

- [ ] **S05: Retire system and user control JSON** `risk:medium` `depends:[S03]`
  > After this: System lock/broadcast state, user restrictions/banners/expiry, and token-version force logout are DB-owned and continue working after `data/system-control.json` and `users/<id>/control.json` are absent.

- [ ] **S06: Retire support-messages JSON** `risk:low` `depends:[S01]`
  > After this: Support submissions, admin listing, and status updates use a `support_messages` DB table and continue working without `data/support-messages.json`.

- [ ] **S07: Retire notification JSON outbox and feed event ambiguity** `risk:medium` `depends:[S01,S04]`
  > After this: Notification listing, unread counts, delivery updates, mark-read, and channel publish dedupe use `notifications_outbox`; legacy notification JSON is archive-only. Feed events are either modeled explicitly or classified as non-canonical artifacts.

- [ ] **S08: Retire report index JSON and decide report artifact ownership** `risk:high` `depends:[S02,S07]`
  > After this: Report feed/index routes use `report_batches` and `report_index` as source of truth; report detail artifacts have an explicit ownership model with working reads and no accidental local canonical index files.

- [ ] **S09: Retire strategy JSON as canonical state** `risk:medium` `depends:[S08]`
  > After this: Quick check, daily/full/deep-dive, report views, and strategy exports use the `strategies` table as canonical; `strategy.json` is absent, derived, or export-only.

- [ ] **S10: Retire state.json for lifecycle and onboarding state** `risk:high` `depends:[S03,S04,S09]`
  > After this: Onboarding, bootstrap progress, active-user eligibility, pending deep dives, last daily/full report timestamps, and state transitions are DB-owned and continue working without `data/state.json`.

- [ ] **S11: Retire portfolio.json as canonical holdings** `risk:high` `depends:[S10]`
  > After this: Portfolio API, risk snapshots, strategy baseline inputs, and active-user eligibility derive holdings from `position_transactions`/portfolio DB state and match legacy portfolio JSON fixtures before `portfolio.json` is demoted.

- [ ] **S12: Stop provisioning retired product-state files and document deploy-anywhere blockers** `risk:medium` `depends:[S02,S03,S04,S05,S06,S07,S08,S09,S10,S11]`
  > After this: New user workspaces contain only legitimate workspace/prompt/artifact scaffolding, not retired DB-owned JSON state; docs list remaining deploy-anywhere blockers and service-splitting candidates.

## Boundary Map

### State ownership categories

Produces:
- `Postgres product state`: operational/user-facing/cross-session/queryable state owned by backend tables.
- `Derived artifact`: regenerated/exported files whose loss does not destroy product truth.
- `Workspace prompt`: user/agent prompt material such as `USER.md`.
- `Cold archive`: historical material retained for audit/debugging, not live reads.
- `Disposable cache`: external/cache data safe to evict.

### Migration contract

Produces:
- Idempotent migration scripts with dry-run default.
- Parity verifiers comparing legacy file fixtures to DB rows until cutover.
- `migration_archive` entries before destructive deletion/archive.
- Feature flags or rollback paths where user lockout/orchestration risk exists.

### Backend ownership invariant

Downstream slices consume the invariant that completed domains must not read or write `users/*` or root `data/*` JSON as canonical production state.
