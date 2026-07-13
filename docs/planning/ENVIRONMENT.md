# P5 Environment Manifest — 2026-07-12, branch `feat/19-p5-frontend`. **Gate: GREEN.**

First **frontend** environment. All FE-local under `frontend/ui`; backend untouched. Run commands
from `frontend/ui`.

| # | Service | Status | Verify |
|---|---|---|---|
| E1 | Node 20 / pnpm | ✅ node 20.20.2 · pnpm 10.33.4 | `node -v`, `pnpm -v` |
| E2 | Vite/React/TS scaffold + `pnpm install` | ✅ | `pnpm build` clean (tsc --noEmit + vite build; 122 modules, ~107 kB gzip) |
| E3 | Vite dev server | ✅ :5173 | `pnpm dev`; proxy `/api` → backend `:8001` (same-origin so the session cookie flows) |
| E4 | Uvicorn backend (DuckDB) + seed | ⏸ used at Gate C | `uv run uvicorn app.main:app --port 8001`; needed only for the full E2E flow |
| E5 | eslint + prettier | ✅ clean | `pnpm lint`, `pnpm format:check` |
| E6 | vitest + Testing-Library + MSW | ✅ 13 pass | `pnpm test`; MSW mocks the API (no backend for unit/component) |
| E7 | Playwright + chromium | ✅ downloaded (v1228) + trivial E2E passes | `pnpm e2e` (redirect-to-login smoke) — **G-P5b resolved, no fallback needed** |
| E8 | tsc strict | ✅ 0 err | `pnpm typecheck` |

Resolved versions: TypeScript **5.9.3** (TS 6.0 not yet published — `.prompticorn` aspirational `v6.0`
tracked as a later bump), Vite 6.4.3, React 19.2, Vitest 3.2, MSW 2.15, React Router 7, TanStack Query 5.
New toolchain (G-P5a, all FE-local): React · Vite · @vitejs/plugin-react · TypeScript · vitest ·
@testing-library/{react,jest-dom,user-event} · MSW · @playwright/test · TanStack Query · React Router ·
eslint (flat) + typescript-eslint · prettier · axe-core.
Readiness: `P5_ENV_READY=GREEN`.

---

# P0 Environment Manifest (live)

Stood up by the env-setup gate on 2026-06-25, branch `feat/14-p0-stabilize`. The pipeline owns
all of this — no manual steps required. **Gate status: GREEN.**

| # | Service / process | Status | Start command | Verify (health check) | Stop cleanly |
|---|---|---|---|---|---|
| E1 | Python 3.14 toolchain | ✅ 3.14.4 | `uv python pin 3.14 && uv sync` | `uv run python -V`; `uv run python -c "import app.main"` | n/a |
| E2 | DuckDB (embedded) | ✅ 1.5.0 | (driver; opened by app) | `uv run python -c "import duckdb;duckdb.connect(':memory:').execute('SELECT 1')"` | connection closed by lifespan |
| E3 | Uvicorn dev server + reload | ✅ :8001 | `uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload` | `curl localhost:8001/` → 200 | `kill <uvicorn pid>` (bg task `bimz3imc2`) |
| E4 | pyright (types) | ✅ 0 err baseline | `uv run pyright app` (or `-w` to watch) | first pass 0 errors | `kill` watcher |
| E5 | ruff (lint) | ✅ 13 err baseline | `uv run ruff check .` | exit code / error count | n/a |
| E6 | pytest runner | ✅ 46 pass / 1 known-fail | `uv run pytest -q` | suite runs | n/a |
| E7 | Docker daemon | ✅ 29.1.3 | (system) | `docker version`; image build after L1 (#21) | `docker rm -f <container>` |

## Captured baselines (so lanes know the starting state)

- **ruff:** 13 errors (9 auto-fixable) — lanes/enforcement clear these.
- **pytest:** `46 passed, 1 failed`. The single failure
  `tests/queries/versions/test_retrieve_version_history.py::test_retrieve_version_history`
  is **pre-existing** (asserts plain dicts, code returns `ApplicationAndVersionResponseModel`) —
  **not introduced by P0**. The lane touching version retrieval (or the aggregator) decides
  whether to align it; otherwise it is a documented pre-existing red.
- **pyright:** 0 errors on `app/` (standard mode).

## New dependency added (flagged)

- `httpx` → **dev** group. Required by FastAPI/Starlette `TestClient`; without it the test suite
  cannot even collect. Test-infra only; not shipped runtime code.

## To tear everything down

```bash
kill $(pgrep -f 'uvicorn app.main:app')   # E3 server + reloader
# E1/E2/E5/E6/E7 are on-demand or system-managed; nothing else to stop.
```

---

# P2 Environment Manifest (live) — 2026-07-11, branch `feat/16-p2-release-integration`

Stood up by the env-setup gate for the P2 resource wave. **Gate status: GREEN.**

| # | Service / process | Status | Verify (health check) | Notes |
|---|---|---|---|---|
| E1 | Python 3.14 / uv | ✅ 3.14.4 | `uv run python -V`; `import app.main` OK | — |
| E2 | DuckDB (embedded) | ✅ | `releases`+`release_components` present after boot; `GET /ready`→200 | — |
| E3 | Uvicorn `:8001 --reload` | ✅ boots (health/ready 200) | `curl :8001/health`→200 | **kept DOWN during pytest** (see protocol) |
| E4 | pyright (strict) | ✅ 0 errors | `uv run pyright` | one-shot at each checkpoint; `-w` available |
| E5 | ruff | ✅ clean | `uv run ruff check app tests` | one-shot at each checkpoint |
| E6 | pytest + cov | ✅ 194 passed | `uv run pytest -q` | baseline (server down) |
| E7 | SSE live smoke | ⏸ deferred | `curl -N :8001/products/{id}/events` | endpoint is a shell pre-R3; smoked at integration gate after R3 lands |
| E8 | Docker | ✅ 29.1.3 | `docker version` | verify-only (P2 doesn't change image) |

## DuckDB single-writer protocol (Gap G4 reconciliation)
DuckDB holds an exclusive lock on its file. The live E3 server and the `pytest` suite both target the
configured `test.db`, so they **cannot run simultaneously** (running both yields ~6 DB-lock failures).
Protocol: **E3 is verified boot-healthy, then kept down while automated `pytest` runs own the DB file;
E3 is brought up fresh (isolated run) only for the live E2E + SSE observation at the integration gate.**
Each parallel resource lane self-verifies inside its own git worktree (own `test.db`), so no cross-lane
or lane-vs-server contention occurs during the fan-out.

## Readiness signal
`P2_ENV_READY=GREEN` — all health checks pass at their appropriate points; resource lanes unblocked.

---

# P4 Environment Manifest — 2026-07-11, branch `feat/18-p4-auth-oss`. **Gate: GREEN.**

| # | Service | Status | Verify |
|---|---|---|---|
| E1 | Python 3.14 / uv | ✅ 3.14.4 | `import app.main`; `from argon2 import PasswordHasher` |
| E2 | DuckDB | ✅ | `users`/`sessions`/`email_verification_tokens` present after boot (post-foundation) |
| E3 | Uvicorn `:8001` | ✅ boots | down during pytest (single-writer protocol) |
| E4 | pyright | ✅ 0 err | one-shot |
| E5 | ruff | ✅ clean | — |
| E6 | pytest | ✅ 257 | baseline |
| E7 | In-process capture Mailer | ⏸ deferred | foundation code; verified at integration (a verification token is retrievable from the sink) |
| E8 | Docker | ✅ 29.1.3 | verify-only |

New dep (flagged): **`argon2-cffi` 25.1.0** (argon2id password hashing) → runtime dependency.
Readiness: `P4_ENV_READY=GREEN`.

---

# P3 Environment Manifest — 2026-07-12, branch `feat/17-p3-multi-db`. **Gate: GREEN.**

| # | Service | Status | Verify |
|---|---|---|---|
| E1 | Python 3.14 / uv | ✅ 3.14.4 | `import app.main`; `import psycopg`; `from testcontainers.postgres import PostgresContainer` |
| E2 | DuckDB (default) | ✅ | 373 suite green on duckdb |
| E3 | Docker daemon | ✅ 29.1.3 | `docker version` |
| E4 | PostgreSQL container | ✅ | testcontainers `postgres:17-alpine` up; `psycopg SELECT 1 → (1,)` |
| E5 | pyright / ruff | ✅ | 0 err / clean |
| E6 | pytest | ✅ 373 | duckdb baseline |
| E7 | Uvicorn `:8001` | ✅ | can point at PG via `LAVS_DB_BACKEND=postgres` for live smoke |
| E8 | testcontainers plumbing | ✅ | disposable PG start/stop proven |

New deps (flagged): **`psycopg[binary]` 3.3.4** (runtime PG driver) · **`testcontainers[postgres]` 4.14.2** (dev/test).
Readiness: `P3_ENV_READY=GREEN`.
