# Verification and Branch Handoff Protocol

This protocol is for branches implemented on another machine and returned for review, fixes, migration, merge, and deployment.

## Before implementation

Read these docs in order:

1. `README.md`
2. `implementation-brief.md`
3. `slice-execution-map.md`
4. `source-artifacts/M001-ROADMAP.md`
5. `source-artifacts/REQUIREMENTS.md`
6. `source-artifacts/DECISIONS.md`

Then inspect the current branch because code may have moved since this package was written.

## Required branch summary

Every returned branch must include a short handoff note with:

- branch name;
- slice ID(s) implemented;
- domains retired or reclassified;
- schema changes and migration names;
- migration dry-run command and output summary;
- parity verification command and output summary;
- tests/builds run and results;
- live legacy file reads/writes removed or guarded;
- legacy paths now archived, derived, prompt, cache, or absent;
- known limitations;
- rollback trigger and rollback steps;
- production migration/deployment notes.

## Required verification classes

### 1. Static ownership guard

A completed slice should have a deterministic check that fails if the retired domain reintroduces live canonical reads/writes against legacy filesystem paths.

Acceptable forms:

- focused unit test;
- static script that scans call sites for retired paths;
- integration test proving absence of file fallback;
- route/service test that runs with legacy files absent.

### 2. Migration safety

Migrations must be:

- idempotent;
- dry-run by default when destructive or archival;
- non-secret-printing;
- explicit about what will be archived/deleted;
- safe to run repeatedly during review.

### 3. Parity proof

Before a legacy canonical file is deleted or demoted, prove DB state matches representative legacy input.

Parity should cover:

- existing live user/domain records when available;
- representative fixtures for edge cases;
- empty/missing legacy file behavior;
- malformed legacy file behavior where relevant.

### 4. Runtime behavior

For each completed domain, verify the user/admin route or service behavior that actually consumes the state.

Examples:

- auth slice: login/JWT/force logout/password change;
- jobs slice: list/detail/supersede/watchdog/trigger;
- portfolio slice: holdings/risk/baseline eligibility;
- notifications slice: unread/list/mark-read/dedupe/delivery update.

### 5. Observability and rollback

High-risk domains must expose enough signal for a later operator to diagnose failure.

At minimum:

- structured errors include domain, user ID where safe, and phase;
- migration logs do not expose secrets;
- archival rows/records can identify what was moved;
- rollback path is documented before deployment.

## Merge acceptance checklist

A returned branch is not ready to merge until:

- [ ] code compiles;
- [ ] relevant backend tests pass;
- [ ] relevant frontend build/lint passes if UI changed;
- [ ] migration dry-run has been executed;
- [ ] parity verifier has been executed;
- [ ] retired legacy files can be absent without breaking the domain;
- [ ] source-of-truth classification is documented;
- [ ] no secrets are printed in logs or test output;
- [ ] rollback steps are written;
- [ ] production report exists if deployment/restart/migration is next.

## Production deployment rule

Before production-touching migration, restart, or deployment, write a production report under `/root/codex/production-reports/` with:

- what is changing;
- why it is changing;
- risks;
- validation and test evidence;
- expected impact;
- rollout plan;
- rollback trigger;
- rollback steps.

This docs package does not itself deploy or migrate anything.

## Review strategy for this repository

When a branch returns here, review in this order:

1. read the handoff note;
2. inspect schema/migrations first;
3. inspect service and route source-of-truth changes;
4. run migration dry-run;
5. run parity verification;
6. run targeted tests;
7. run broad backend/frontend verification as needed;
8. fix regressions locally if small;
9. merge only after verification evidence is current;
10. deploy/migrate only with a production report.
