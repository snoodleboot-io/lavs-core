# LAVS - Lowercase Acronym Versioning System

**Repository:** `C:/Users/johna/code/lavs`  
**Current Branch:** `main`  
**Version:** 0.1.0 (WIP - Do Not Use)

---

## Executive Summary

LAVS is a **Version Management REST API** designed to track software versions across multiple applications and components in complex, distributed systems. It provides a centralized system to maintain semantic versions for products, libraries, microservices, and other software components that need coordinated versioning but may not share the same version number.

> **Status:** This is a work-in-progress project. The README explicitly states "WIP - Do not use at this time."

---

## Architecture Overview

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Runtime** | Python 3.13+ |
| **Framework** | FastAPI |
| **Database** | DuckDB (primary, current) |
| **ORM/Query** | Raw SQL via DuckDB |
| **Validation** | Pydantic v2 |
| **Server** | Uvicorn |
| **Deployment** | Kubernetes via Helm |

### Project Structure

```
lavs/
├── app/                          # Main application code
│   ├── main.py                   # FastAPI entry point
│   ├── configurations/           # Configuration management
│   │   ├── configuration.py       # Pydantic configuration model
│   │   ├── database.yaml         # Database schema definitions
│   │   └── root_dir.py           # Path utilities
│   ├── connections/              # Database connection abstraction
│   │   ├── connection.py         # Abstract base class
│   │   ├── connection_factory.py # Factory for creating connections
│   │   └── duckdb_connection.py  # DuckDB implementation
│   ├── database/                 # Database management
│   │   ├── database_manager.py   # Table lifecycle management
│   │   └── duckdb/ddl.sql       # SQL schema definitions
│   ├── models/                   # Pydantic data models
│   │   ├── requests/            # Request models
│   │   └── respones/            # Response models (note: typo in directory name)
│   ├── queries/                  # Data access layer
│   │   ├── query.py             # Base query class
│   │   ├── crud/                # Basic CRUD operations
│   │   ├── versions/            # Version management queries
│   │   └── patch_version/       # Patch-specific operations
│   ├── routers/                  # API route handlers
│   │   ├── basic_crud.py        # Generic CRUD endpoints
│   │   ├── patch.py             # Patch version endpoints
│   │   └── versions.py         # Version management endpoints
│   ├── security/                # Security module (EMPTY)
│   └── utils/                    # Utilities
├── tests/                        # Test suite
├── helm/                         # Kubernetes Helm charts
└── documentation_images/         # Architecture diagrams
```

---

## Core Components

### 1. Configuration Layer

**Location:** [`app/configurations/`](app/configurations/)

- **[`configuration.py`](app/configurations/configuration.py)**: Pydantic model storing:
  - `version`: int (default: 0)
  - `application_name`: str (default: "lavs-api")
  - `database_name`: str (default: "test.db")

- **[`database.yaml`](app/configurations/database.yaml)**: YAML configuration for database schema (TODO: Multi-database support not yet implemented)

- **[`root_dir.py`](app/configurations/root_dir.py)**: Utility function to find source root directory

### 2. Database Layer

**Location:** [`app/database/`](app/database/)

**DDL Schema** ([`ddl.sql`](app/database/duckdb/ddl.sql)):
```sql
CREATE TABLE IF NOT EXISTS Versions (
    major INTEGER,
    minor INTEGER,
    patch INTEGER,
    product_name VARCHAR,
    id INTEGER PRIMARY KEY
);
CREATE SEQUENCE IF NOT EXISTS version_id_seq START 1;
```

**[`database_manager.py`](app/database/database_manager.py)**: Manages table lifecycle:
- `create_tables()`: Creates Versions table
- `drop_tables()`: Drops Versions table

### 3. Connection Layer

**Location:** [`app/connections/`](app/connections/)

**Abstract Base Class** ([`connection.py`](app/connections/connection.py)):
- Defines interface for database connections
- Methods: `execute()`, `fetchdf()`, `connection()`

**DuckDB Implementation** ([`duckdb_connection.py`](app/connections/duckdb_connection.py)):
- Connects to DuckDB database file
- Uses context manager for connection lifecycle

**Factory** ([`connection_factory.py`](app/connections/connection_factory.py)):
- Registry pattern for connection types
- Currently supports: `duckdb` only
- TODO: MySQL, PostgreSQL, SQL Server, MongoDB (mentioned in README)

### 4. Request/Response Models

**Location:** [`app/models/`](app/models/)

**Request Models:**
| Model | File | Purpose |
|-------|------|---------|
| `RequestModel` | [`requests/request_model.py`](app/models/requests/request_model.py) | Base Pydantic model |
| `ApplicationNameModel` | [`requests/application_name_model.py`](app/models/requests/application_name_model.py) | Product name only |
| `ApplicationAndVersionNameModel` | [`requests/application_and_version_model.py`](app/models/requests/application_and_version_model.py) | Product name + semantic version |

**Response Models:**
| Model | File | Purpose |
|-------|------|---------|
| `ResponseModel` | [`respones/response_model.py`](app/models/respones/response_model.py) | Base response |
| `ApplicationAndVersionResponseModel` | [`respones/applciation_and_version_response_model.py`](app/models/respones/applciation_and_version_response_model.py) | Full version info |
| `PatchResponseModel` | [`respones/patch_response_model.py`](app/models/respones/patch_response_model.py) | Patch-only response |

**Note:** There are typos in the codebase:
- Directory `respones/` should be `responses/`
- File `applciation_and_version_response_model.py` should be `application_and_version_response_model.py`

### 5. Query Layer

**Location:** [`app/queries/`](app/queries/)

**Base Class** ([`query.py`](app/queries/query.py)):
- Generic async query executor
- Manages connection lifecycle
- Logging and error handling

**CRUD Operations:**
- [`retrieve_all.py`](app/queries/crud/retrieve_all.py): Retrieve all versions

**Version Operations:**
- [`create_version.py`](app/queries/versions/create_version.py): Create new version
- [`delete_version.py`](app/queries/versions/delete_version.py): Delete specific version
- [`retrieve_latest_version.py`](app/queries/versions/retrieve_latest_version.py): Get latest version
- [`retrieve_version_history.py`](app/queries/versions/retrieve_version_history.py): Get full history

**Patch Operations:**
- [`create_patch.py`](app/queries/patch_version/create_patch.py): Increment patch version
- [`read_current_patch.py`](app/queries/patch_version/read_current_patch.py): Get current patch
- [`rollback_to_previous_patch_version.py`](app/queries/patch_version/rollback_to_previous_patch_version.py): Rollback patch

### 6. API Routers

**Location:** [`app/routers/`](app/routers/)

**Main Entry** ([`app/main.py`](app/main.py)):
```python
app = FastAPI()
app.include_router(patch.router)
app.include_router(basic_crud.router)
app.include_router(versions.router)
```

**Endpoints:**

| Router | Prefix | Method | Endpoint | Description |
|--------|--------|--------|----------|-------------|
| `basic_crud` | `/crud` | GET | `/read_all` | Read all versions |
| `patch` | `/patch` | POST | `/` | Create new patch version |
| `patch` | `/patch` | GET | `/` | Read current patch |
| `patch` | `/patch/rollback` | POST | `/rollback` | Rollback to previous patch |
| `versions` | `/versions` | GET | `/` | Get version history |
| `versions` | `/versions/latest` | GET | `/latest` | Get latest version |
| `versions` | `/versions` | POST | `/` | Create new version |
| `versions` | `/versions` | DELETE | `/` | Delete version |

---

## Deployment

**Location:** [`helm/`](helm/)

**Chart Metadata:**
- Name: `lavs`
- Version: 0.1.0
- App Version: 1.16.0

**Deployment Configuration:**
- Default replica count: 1
- Service type: ClusterIP
- Port: 80
- Health checks: HTTP GET on `/`
- Ingress: Disabled (configurable)

---

## Test Coverage

**Test Files:** 14 tests collected

| Category | Tests |
|----------|-------|
| Configuration | 1 |
| Connections | 2 |
| Database | 2 |
| Models | 3 |
| Queries | 6 |

**Current Status:** 10 FAILED, 4 PASSED

**Failed Tests (Critical Bug):**
The connection layer has a bug in [`connection_factory.py`](app/connections/connection_factory.py:22):

```python
# BUG: Should be .connection() not .connection
with self.__registry[key]().connection as conn:
```

The `DuckDBConnection.connection` method is decorated with `@contextlib.contextmanager`, so it must be called as `.connection()` to return the generator, not used directly as a context manager.

---

## Identified Gaps and Issues

### Critical Issues

1. **Connection Factory Bug** (10 test failures)
   - File: [`app/connections/connection_factory.py`](app/connections/connection_factory.py:22)
   - Issue: `.connection` should be `.connection()`
   - Impact: All database operations fail at runtime

2. ~~SQL Syntax Error~~ - FIXED: [`retrieve_all.py`](app/queries/crud/retrieve_all.py) had `WHERE ORDER BY` - removed invalid WHERE clause

3. **SQL Injection Vulnerabilities**
   - Files: Multiple query files use f-strings for SQL
   - Examples:
     - [`create_version.py`](app/queries/versions/create_version.py:34)
     - [`delete_version.py`](app/queries/versions/delete_version.py:30)
     - [`retrieve_version_history.py`](app/queries/versions/retrieve_version_history.py:27)
     - [`retrieve_latest_version.py`](app/queries/versions/retrieve_latest_version.py:32)
   - Fix: Use parameterized queries

### Typographical Errors (FIXED)

4. ~~Directory Name Typo~~ - FIXED: Renamed `respones/` to `responses/`
5. ~~File Name Typo~~ - FIXED: Renamed `applciation_and_version_response_model.py` to `application_and_version_response_model.py`
   - Updated 17 import statements across the codebase

### Missing Components

6. **Empty Security Module**
   - Location: [`app/security/`](app/security/)
   - Status: Directory exists but is empty
   - TODO: Authentication/Authorization not implemented

7. **Multi-Database Support Not Implemented**
   - README mentions planned support for MySQL, PostgreSQL, SQL Server, MongoDB
   - [`database.yaml`](app/configurations/database.yaml) has TODO comment
   - [`connection_factory.py`](app/connections/connection_factory.py) only supports `duckdb`

8. **Missing Tests**
   - No router/integration tests
   - No API endpoint tests
   - No security tests (directory exists but empty)
   - Test directory structure exists but unused: `tests/integration/`, `tests/slow/`, `tests/unit/`

9. **Configuration Management**
   - No environment variable support
   - No config file loading (database.yaml not actually used)
   - TODO in database.yaml suggests multi-database schema not implemented

### Code Quality Issues

10. **Docstrings Missing**
    - Several files missing docstrings
    - `ApplicationAndVersionResponseModel` has empty docstring

11. **Incomplete Error Handling**
    - Generic exception catching in [`query.py`](app/queries/query.py:30)
    - No specific error types

12. **Hardcoded Values**
    - Database name: "test.db" in Configuration

---

## Data Flow

```
HTTP Request
    ↓
FastAPI Router (app/routers/)
    ↓
Request Model Validation (Pydantic)
    ↓
Query.execute() (app/queries/)
    ↓
ConnectionFactory.retrieve()
    ↓
DuckDBConnection.connection()
    ↓
Raw SQL Execution
    ↓
Response Model Serialization
    ↓
HTTP Response
```

---

## Roadmap (Based on README)

1. **Current (0.1.0)**: DuckDB support only - BROKEN
2. **Planned**: MySQL support
3. **Planned**: PostgreSQL support
4. **Planned**: SQL Server support
5. **Planned**: MongoDB support (maybe)
6. **Planned**: Authentication layer (optional)

---

## Dependencies

**Runtime:**
- `duckdb>=1.5.0`
- `fastapi>=0.135.1`
- `pydantic>=2.12.5`
- `uvicorn>=0.40.0`

**Development:**
- `pytest>=9.0.2`
- `pytest-cov>=7.0.0`
- `ruff>=0.8.0`
- `pre-commit>=4.0.0`
- `pyright>=1.1.389`
- `build>=1.0.0`

---

## Summary

LAVS is an ambitious project designed to solve a real problem: managing versions across complex, distributed software systems. However, it is currently in an early, broken state:

- ~~Cannot run~~: SQL syntax error and typos fixed
- ~~Typographical issues~~: Directory and file naming errors corrected

The project has good architectural foundations (separation of concerns, factory pattern, Pydantic validation) but requires significant work before it can be considered usable.

---

*Generated: 2026-03-10*
*Repository: C:/Users/johna/code/lavs*
