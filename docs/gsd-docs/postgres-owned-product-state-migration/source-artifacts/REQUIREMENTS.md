# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R001 — Backend/Postgres must be the source of truth for production application state, with filesystem limited to prompts, derived artifacts, cold archives, and disposable caches.
- Class: quality-attribute
- Status: active
- Description: Backend/Postgres must be the source of truth for production application state, with filesystem limited to prompts, derived artifacts, cold archives, and disposable caches.
- Why it matters: Filesystem-owned production data made the system fragile, VPS-bound, hard to back up, hard to deploy across environments, and difficult to trust operationally.
- Source: user-directed DB/backend migration phase
- Validation: For each migrated domain, live backend reads/writes use Postgres, migration parity is verified, legacy filesystem writes are removed or guarded, and retained filesystem paths are explicitly classified as artifact/cache/archive/prompt.

### R002 — The product architecture must move toward portable deployments with managed backups, multiple environments, and GitOps-compatible infrastructure.
- Class: operability
- Status: active
- Description: The product architecture must move toward portable deployments with managed backups, multiple environments, and GitOps-compatible infrastructure.
- Why it matters: The current VPS/local-filesystem model limits reliability, repeatable deployments, backups, environment isolation, and future service splitting.
- Source: user-directed DB/backend migration phase
- Validation: Milestone outputs reduce host-local state assumptions, make DB ownership explicit, and document remaining blockers to deploy-anywhere infrastructure.

## Validated

## Deferred

## Out of Scope

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | quality-attribute | active | none | none | For each migrated domain, live backend reads/writes use Postgres, migration parity is verified, legacy filesystem writes are removed or guarded, and retained filesystem paths are explicitly classified as artifact/cache/archive/prompt. |
| R002 | operability | active | none | none | Milestone outputs reduce host-local state assumptions, make DB ownership explicit, and document remaining blockers to deploy-anywhere infrastructure. |

## Coverage Summary

- Active requirements: 2
- Mapped to slices: 2
- Validated: 0
- Unmapped active requirements: 0
