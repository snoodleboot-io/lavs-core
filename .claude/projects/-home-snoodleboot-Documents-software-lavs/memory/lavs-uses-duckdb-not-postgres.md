---
name: lavs-uses-duckdb-not-postgres
description: LAVS persists with DuckDB and raw SQL — no PostgreSQL, no ORM
metadata:
  type: project
---

LAVS uses **DuckDB** (`duckdb>=1.5.0`) with **raw SQL** — no ORM. DDL lives at `app/database/duckdb/ddl.sql`; access goes through `app/database/database_manager.py` and `app/connections/`.

**Why:** The `.prompticorn.yaml` config historically defaulted `database: PostgreSQL` / `orm: SQLAlchemy`, which were never accurate — neither Postgres nor SQLAlchemy appears in the deps. Corrected the yaml to `database: DuckDB`, `orm: none (raw SQL)`.

**How to apply:** Don't suggest SQLAlchemy/Postgres patterns. Backend Python code lives in `app/` (not the near-empty `backend/api/` mount point declared in config). Related: [[claude-conventions-are-generated]].
