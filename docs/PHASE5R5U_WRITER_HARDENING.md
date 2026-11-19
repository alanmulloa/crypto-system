# Phase 5R–5U — Research Main-Writer Hardening

This macro-block removes a repository-level race condition between automated
research workflows that commit evidence directly to `main`.

## Phase 5R — Shared writer lock

All research workflows that write to `main` use the same GitHub Actions
concurrency group:

```text
research-main-writer
```

This serializes Phase 5G, generic Phase 5H and Phase 5M evidence writers.

## Phase 5S — Safe rebase-before-push

Each writer:

1. checks out `main` with full history
2. generates and commits only its evidence
3. runs `git pull --rebase origin main`
4. pushes `HEAD:main`

If a human merge or another change lands during the run, the writer rebases
before pushing. A real conflict fails safely instead of forcing over remote
history.

## Phase 5T — Writer policy audit

A deterministic audit verifies every known research main-writer has:

- `contents: write`
- the shared concurrency group
- `cancel-in-progress: false`
- `fetch-depth: 0`
- rebase-before-push
- explicit `HEAD:main` push

The audit runs in CI for workflow/policy changes.

## Phase 5U — Writer hardening completion

The repository now has one serialized, auditable main-writing path for research
evidence. This changes only operational durability; it does not affect strategy
research, lifecycle decisions or execution permissions.

```text
strategy mutation = false
automatic registration = false
automatic Phase 6 activation = false
phase6_blocked = true
```
