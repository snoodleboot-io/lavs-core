# P1 Domain Model — Multiagent Parallel Execution Plan

> **Status:** ▶ **EXECUTING (2026-06-29).** Env-setup gate green (py3.14.4, ruff/pyright clean,
> 90 baseline tests pass, `python-ulid==3.1.0` added). Branch `feat/15-p1-domain-model` cut from
> `main`. Epic **#15**. Predecessor: P0 (#14) merged.
> **Author:** orchestrator (harness) · **Persona model:** see CLAUDE.md agent registry.

This document is the canonical companion to `P0_MULTIAGENT_EXECUTION_PLAN.md`, applying the **same
harness pattern** to **P1 — Domain model** (`ROADMAP.md` P1 · `API_CONTRACT.md §3`).

## 0. Reconciliation (unchanged from P0 §0)
Project agent `.md` files are **personas / convention-carriers**; genuine execution is performed by
**harness-native parallel subagents** (`Agent`/`Workflow`), file-mutating lanes isolated in **git
worktrees**. Where a sub-lane group is bound by a hard dependency spine *and* a shared lockfile
change (the P1 **foundation**), it is executed as a tight **sequence of focused subagents** rather
than forced into conflicting parallel worktrees — same intent, no lockfile/venv thrash. Genuine
parallelism is realized in the **resource wave**, whose lanes are file-disjoint by construction.

## 1. Goal & scope
**Goal:** replace the flat `Versions` table with `products → components → immutable versions`
(status `active|superseded|rolled_back`); config-driven schema init; refactor `/versions` & `/patch`
onto the model; **mutations move from query-params to JSON bodies**; rollback marks status, never
deletes. **Acceptance:** register product → components → versions; full history retained & queryable.

**Decisions:** ULID string ids (`python-ulid`; wire-compatible with API_CONTRACT's "uuid string",
"latest" stays **semver**-ordered) · idempotent **inspect-then-migrate** of flat data · clean
refactor, **no compat shim**.

**Out (later phases):** releases/manifest/SSE (**P2**) · pluggable auth providers (**P4**, keep P0
`X-API-Key`) · multi-DB dialect DDL (**P3**, DuckDB only here).

## 2. Execution map
```
env-setup gate ✅  (py3.14/uv, ruff, pyright, pytest, +python-ulid, branch feat/15)
  │
  ▼  Wave F — FOUNDATION (sequential focused subagents; coupled spine + shared lockfile)
  ├─ Foundation-A · code/backend persona
  │     F1  domain models + ComponentKind/VersionStatus enums + ULID id type (port semver logic)
  │     F2a ddl.sql (products/components/versions, ULID PK/FK, status CHECK, created_at)
  │         + config-driven init (database.yaml tables[] · configuration.py) + database_manager rewrite
  │         + conftest reconciled to the config-driven init path
  ├─ Foundation-B · backend persona  (after A)
  │     F2b widen Query[T] TypeVar · lifespan schema-init+migration wiring · repository base
  │         · shared error-envelope handler · pre-create 5 router shells + register in main.py
  │         · delete legacy routers/queries/tests (basic_crud, old versions/patch, crud/ etc.)
  │     F2c idempotent flat→relational migration
  │
  ▼  🔒 FOUNDATION GATE  — app boots, new tables init, migration runs, /health,/ready 200, suite green
  │
  ▼  Wave R — RESOURCES (parallel worktrees off the foundation commit; shared venv; each forks TDD)
  ├─ R1 products router+queries (list, create 409-dup, get 404, /{id}/components)        ⟂
  ├─ R2 components router+queries (create 404-unknown-product, /components/{id}/versions) ⟂
  ├─ R3+R4 versions lifecycle (POST /versions immutable 404-unknown-component;            ⟂
  │        POST /versions/{id}/rollback status-mark + reactivate-prior, no delete)
  └─ R5 timeline composite GET /products/{id}/timeline (read-only; aggregated last)       ⟂
  ⟂  ATDD spec lane — acceptance scenarios from P1 exit criteria + API_CONTRACT §3
  │
  ▼  aggregate (R5 last) → Gate A enforcement → Gate B security → Gate C integration
  │   → green = P1 done · else debug-agent localizes → re-run failing lane only (max 2×) → escalate
```

## 3. Shared-file ownership (the merge-conflict surface — Foundation owns all of these)
`main.py` (registration+lifespan) → F2b · `query.py` (TypeVar) → F2b · `configuration.py`+`database.yaml`
→ F2a · `ddl.sql` → F2a · `database_manager.py` → F2a · `tests/integration/conftest.py` → F2a ·
`pyproject.toml`/`uv.lock` (`python-ulid`) → env-gate (done) · shared **error-envelope** handler → F2b ·
legacy deletions → F2b. Resource lanes touch **only their own** `app/routers/<r>.py`, `app/queries/<r>/*`,
and `tests/.../<r>` — disjoint by construction.

## 4. Migration mapping (flat → relational)
one product / distinct `product_name` · one synthetic `component` ("default", kind `service`) / product ·
one `version` / flat row (carry major/minor/patch, prerelease NULL, **preserve status 1:1**, ULID id).
Idempotent: migrate only when target `products` empty AND a `Versions` table has rows; leave `Versions`
vestigial.

## 5. Convention gates
Gate A enforcement (1-class-1-file · snake_case filenames · no constants→enum/config · `T|None`, no
`cast`/`setattr` · `__init__.py` · SOLID) · Gate B security (parameterized SQL only · auth dep on all
routers · no secrets · anchored semver) · Gate C integration (ruff + pyright-strict + pytest+coverage
L80/B70/F90/S85 · app boots · migration verified · ATDD scenarios pass · docker builds).
