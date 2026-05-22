# Implementation Brief — Postgres-Owned Product State Migration

## Problem

The product still has production application state owned by local filesystem JSON under root runtime data and per-user workspaces. That creates fragile deployment semantics:

- host-local state is hard to back up consistently;
- multiple environments are difficult to reason about;
- GitOps-compatible rollout is blocked by mutable state outside the database;
- future service splitting is harder because state ownership is implicit;
- old OpenClaw-era workspace assumptions keep leaking into backend behavior.

The target architecture is not "better file services." The target is backend/Postgres ownership of live product state.

## Goal

Retire filesystem ownership domain-by-domain until live backend reads and writes for core product state use Postgres, while retained filesystem paths are explicitly classified as prompts, derived artifacts, cold archives, or disposable caches.

## Non-goals

- Do not preserve legacy filesystem facades as a stable architecture.
- Do not bulk-edit sensitive user workspaces as a shortcut.
- Do not replace one hidden source of truth with another.
- Do not move prompt files, derived artifacts, or disposable caches into Postgres just because they are files.
- Do not do deploy-anywhere infrastructure work inside this milestone unless it is required to remove filesystem product-state ownership.

## Architectural invariants

1. Backend/Postgres owns operational, user-facing, cross-session, queryable production state.
2. Filesystem bridges are temporary and exist only for import, parity, rollback, or archive creation.
3. Destructive migrations are dry-run by default and archive old state before removal.
4. Parity must be proven before deleting or demoting a legacy canonical file.
5. Completed domains must not continue live reads or writes against retired `users/*` or root `data/*` JSON paths.
6. New user provisioning must stop creating retired DB-owned state files.
7. User workspace files remain acceptable only when they are prompts, agent-local artifacts, caches, exports, or cold archives.

## Requirements covered

- `R001`: Backend/Postgres must be the source of truth for production application state. Filesystem is limited to prompts, derived artifacts, cold archives, and disposable caches.
- `R002`: Architecture must move toward portable deployments with managed backups, multiple environments, and GitOps-compatible infrastructure.

## Decision covered

- `D001`: Retire filesystem ownership domain-by-domain. Temporary bridges are import/parity only, not preserved architecture.

## Implementation approach

Work in thin vertical slices. Each slice should retire one ownership domain or establish safety needed by downstream slices. Prefer existing tables and data-access layers where they already model the domain. Add schema only when a real product-state gap appears.

When adding schema, extend the typed database layer and migration SQL rather than creating backend-owned files under user folders.

## Sensitive-path rule

Per-user workspace data is sensitive. Do not bulk-modify it unless the slice explicitly requires migration/archive of a specific product-state path. Prefer fixing backend source-of-truth code and migration scripts over hand-editing user artifacts.

## Branch handoff expectation

Implementation will happen elsewhere. Completed branches should be handed back with:

- branch name;
- slice(s) implemented;
- schema migrations added, if any;
- migration command and dry-run output;
- parity verification output;
- test/build output;
- paths retired or reclassified;
- rollback notes;
- deployment/migration notes.

This repository can then review, fix if needed, merge, migrate, and deploy.
