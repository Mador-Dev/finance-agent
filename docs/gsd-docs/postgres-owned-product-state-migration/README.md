# Postgres-Owned Product State Migration

## Purpose

This package is the handoff documentation for implementing the `M001 — Postgres-Owned Product State Migration` milestone on another machine or with another model.

The milestone is not a legacy-filesystem cleanup pass. It is a source-of-truth migration:

> Retire OpenClaw-era and VPS-local filesystem ownership of production application state. Move live backend reads and writes to Postgres-owned state. Keep filesystem only for prompts, derived artifacts, cold archives, and disposable caches.

## Reader and expected action

Reader: an implementation agent or engineer arriving cold on a fresh clone.

After reading this package, the reader should be able to:

1. understand the architectural rule for the milestone;
2. pick the next slice in dependency order;
3. implement it without preserving filesystem ownership as architecture;
4. verify parity, migration safety, and absence of live legacy reads/writes;
5. hand a completed branch back for review, fixes, migration, merge, and deployment.

## Documents in this package

- [Implementation brief](implementation-brief.md) — why this milestone exists, what is in and out of scope, and the architectural invariants.
- [Slice execution map](slice-execution-map.md) — all 12 slices, dependencies, touched domains, DB expectations, and completion proof.
- [Verification and branch handoff protocol](verification-and-handoff.md) — what every implementation branch must prove before it is accepted.
- [Source artifacts](source-artifacts/) — copied GSD source artifacts for traceability:
  - `M001-ROADMAP.md`
  - `REQUIREMENTS.md`
  - `DECISIONS.md`
  - `STATE.md`

## Canonical implementation stance

Every touched legacy path must end each slice in exactly one category:

| Category | Meaning |
|---|---|
| Postgres product state | Backend/Postgres is the source of truth for operational, user-facing, cross-session, queryable state. |
| Derived artifact | File can be regenerated or exported; it is not canonical truth. |
| Workspace prompt | Legitimate user/agent prompt material that still belongs in the workspace. |
| Cold archive | Historical/debug material retained for audit or rollback, not live reads. |
| Disposable cache | Safe to evict; not backed up as product truth. |

Anything outside these categories is suspect and should be resolved before the slice is considered done.

## Active GSD status at package creation

- Active milestone: `M001 — Postgres-Owned Product State Migration`
- Active slice: `S01 — State ownership inventory and migration safety gates`
- Phase: planning
- Implementation done in this repository during packaging: none

## Relationship to `.gsd/`

The repository's live `.gsd/` directory remains the local planning database/artifact store. This docs package exists so the milestone can be implemented elsewhere without relying on this session or a local GSD runtime.

If the other machine uses GSD, it can import or recreate plans from these docs. If it does not, this package is still sufficient as a plain Markdown implementation contract.
