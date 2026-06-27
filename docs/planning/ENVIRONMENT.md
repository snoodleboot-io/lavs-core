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
