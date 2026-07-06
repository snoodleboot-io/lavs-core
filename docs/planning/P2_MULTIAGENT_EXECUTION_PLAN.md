# P2 Release Integration ⭐ — Multiagent Parallel Execution Plan

> **Status:** ▶ **EXECUTING (2026-07-06).** Branch `feat/16-p2-release-integration` off `main`
> (P1 merged @ `d09b185`). Commit signing active (SSH). Epic #16 · Linear *P2 — Release integration*
> (LAV-16…LAV-20). Same harness pattern as P0/P1.

The core-value phase: derive a **coherent product version** by snapshotting component versions into
an immutable, reproducible **release manifest**. Companion to `P1_MULTIAGENT_EXECUTION_PLAN.md`.
Contract: `API_CONTRACT.md` §5 (Cut Release) · §6 (SSE) · §3 (schemas).

## 1. Goal & scope
**Goal:** `releases` + `release_components` pinning one `version_id` per component; **cut** a release
(snapshot each component's `active` version, server auto-increments `product_version` by **minor**
bump from the product's `base_version`, persist immutable), **read** the ledger + a frozen manifest,
and a **live SSE** channel emitting `version.created` / `version.rolled_back` / `release.cut`.
**Exit criteria:** given N components at mixed versions, produce and retrieve a single coherent
product release manifest; a cut release never changes afterward.

**Locked decisions:** client cannot set the version (server-owned, minor bump from per-product
`base_version` default `0.0.0`, so first cut → `0.1.0`) · `Idempotency-Key` header dedups double-cut ·
all three SSE event types implemented (in-process async bus) · DuckDB only (multi-DB is P3).
**Out:** frontend consumption (P5), auth providers (P4), multi-DB (P3).

## 2. Execution map
```
env (branch feat/16, signing on)
  ▼ Wave F — FOUNDATION (single coherent lane; coupled spine)
    releases + release_components DDL + base_version on products (config-driven init)
    · CutReleaseModel / ReleaseResponseModel / ReleaseComponentResponseModel
    · product-version derivation helper (minor bump from base)
    · EventBus (async per-product pub/sub) + EventType/DomainEvent, wired into lifespan (app.state.event_bus)
    · releases + events router shells registered
  ▼ 🔒 FOUNDATION GATE — boots, new tables init, event bus up, suite green, pyright/ruff clean
  ▼ Wave R — RESOURCES (parallel worktrees off the foundation commit; each forks TDD)
    ├ R1 ⭐ Cut release: POST /products/{id}/releases {label?,notes?} +Idempotency-Key
    │     snapshot active versions · bump minor · persist immutable release+components · emit release.cut
    ├ R2 Read: GET /products/{id}/releases (ledger) · GET /releases/{id} (frozen manifest)
    ├ R3 SSE: GET /products/{id}/events (text/event-stream) · emit version.created/version.rolled_back
    │     (wired into P1 versions router) + release.cut
    └ ATDD: cut→manifest→derive · immutability after later versions/rollbacks · idempotency · SSE delivery
  ▼ aggregate (R5-style: SSE last) → enforcement → security (param SQL, auth on routers) → integration (ATDD green, boot, E2E)
  ▼ PR to main (signed commits, no --admin needed) → merge
```

## 3. Shared-file ownership (Foundation owns)
`ddl.sql` · `database.yaml`/`configuration.py` · `main.py` (lifespan event bus + router registration) ·
`app/events/*` (bus) · new models · router shells (`releases.py`, `events.py`). Resource lanes touch
only their own routes/queries/tests. **Coupling note:** R3 also edits the P1 `versions` router/queries
to publish `version.created`/`version.rolled_back` — that is R3's alone (R1/R2 don't touch versions.py).

## 4. Cut semantics (frozen)
1. Load the product (404 if unknown). 2. `Idempotency-Key` present & already used for this product →
return the existing release (200/201, no double-cut). 3. Snapshot: for each component, its current
`active` version (components with no active version are skipped, or the cut errors if none — ATDD
pins this; default: include only components that have an active version). 4. `product_version =
minor_bump(latest release version or base_version)`. 5. Insert `releases` + `release_components`
(pinned `version_id`s) — immutable. 6. `event_bus.publish(release.cut)`. 7. Return 201 with the frozen
manifest.

## 5. Gates
Enforcement (1-class/file · snake_case · no constants→enum/config · types · SOLID) · Security
(parameterized SQL only · auth dep on all routers incl. SSE · no secrets) · Integration (ruff +
pyright-strict + pytest+coverage · boot · migration intact · ATDD green · E2E cut/read/SSE).
