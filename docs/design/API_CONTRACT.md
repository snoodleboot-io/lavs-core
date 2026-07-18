# LAVS — FE ↔ BE Contract & Integration Spec

The interface the **Constellation** UI and the LAVS backend both build against. If it isn't
here, the FE can't assume it. Companion to [ARCHITECTURE.md](./ARCHITECTURE.md) ·
[UI_CONCEPT.md](./UI_CONCEPT.md) · [ROADMAP.md](../planning/ROADMAP.md).

> **Decisions locked** (2026-06-24): **OSS is the first cut; EE is a fast-follow.** v1 auth =
> username/password + sessions (signup, email verification, domain allow-list) **and/or** API
> key by deploy config. **EE/Stytch is deferred** — the provider abstraction is designed for
> it now, but no Stytch code ships in v1. Product version on cut = **server auto-increment**.
> Stream freshness = **live (SSE)**.

---

## 1. Editions & auth model

LAVS ships in two editions; **auth is pluggable and selected by deployment config** (env
`LAVS_AUTH_MODES`, a comma list). One or more providers may be enabled at once. **v1 ships
OSS only; EE is a fast-follow** — the abstraction is built for it now, but the Stytch
provider is not implemented in the first cut.

| | OSS (v1) | EE (later) |
|---|---|---|
| Password + sessions | ✅ signup, email verification, domain allow-list | ✅ (or delegated to Stytch) |
| API key (headless/deploy) | ✅ `X-API-Key` | ✅ |
| Managed identity | — | ⏳ **Stytch** (passwordless / SSO / MFA) — *deferred* |
| Config flag | `LAVS_AUTH_MODES=password,apikey` | `LAVS_AUTH_MODES=stytch,apikey` |

### Provider abstraction (backend)

```
AuthProvider:
    authenticate(request) -> Principal | raises 401
Principal = { kind: "user" | "service", id, email?, edition }
```

Implementations: `PasswordSessionProvider`, `ApiKeyProvider` (wraps the existing
[api_key.py](../../app/security/api_key.py)), `StytchProvider`. The request passes if **any**
enabled provider authenticates it. A FastAPI dependency resolves the `Principal` and injects
it into routes (this supersedes the bare-key wiring in P0).

### Authorization (v1)

Authenticated ⇒ allowed. RBAC (org/role scoping) is a **future** item; endpoints are
designed to accept it later (every resource is owned by a product, products by an org).

## 2. Auth flows

### OSS signup + email/domain verification

```mermaid
sequenceDiagram
    participant UI
    participant API
    participant Mail
    UI->>API: POST /auth/signup {email, password}
    API->>API: domain in allow-list? (else 403 domain_not_allowed)
    API->>API: create user (status=pending), hash password
    API->>Mail: send verification token
    API-->>UI: 202 Accepted {status:"pending_verification"}
    UI->>API: POST /auth/verify {token}
    API->>API: activate user (status=active)
    API-->>UI: 200 {user}
```

### OSS login (session cookie)

```mermaid
sequenceDiagram
    participant UI
    participant API
    UI->>API: POST /auth/login {email, password}
    API->>API: verify hash, user active?
    API-->>UI: 200 {user} + Set-Cookie: lavs_session=… (HttpOnly, Secure, SameSite=Lax)
    UI->>API: GET /auth/me  (cookie sent automatically)
    API-->>UI: 200 {user}
```

- Session: opaque server-side session keyed by an `HttpOnly` cookie. `POST /auth/logout` clears it.
- **API key (headless):** clients send `X-API-Key: <key>`; no cookie, no session. Used by CI/pipelines and deploy-configured UIs.
- **EE / Stytch (deferred — not in v1):** UI uses the Stytch SDK; backend verifies the Stytch session JWT on `POST /auth/stytch/callback` and issues its own `lavs_session`. The rest of the API is identical regardless of how the `Principal` was obtained — which is exactly why EE can be added later without touching resource routes.

### Auth endpoints

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/auth/signup` | `{email, password}` | OSS; 403 if domain not allowed; 409 if exists |
| POST | `/auth/verify` | `{token}` | activates a pending user |
| POST | `/auth/login` | `{email, password}` | sets session cookie |
| POST | `/auth/logout` | — | clears session |
| GET | `/auth/me` | — | current principal; 401 if unauthenticated |
| POST | `/auth/stytch/callback` | `{stytch_token}` | EE only — *deferred, not in v1* |

## 3. Resource endpoints

All resource routes require an authenticated `Principal`. Bodies are **JSON** (the current
query-param style is replaced). IDs are UUID strings.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/products` | list products |
| POST | `/products` | create `{name, description?}` |
| GET | `/products/{id}` | one product |
| GET | `/products/{id}/timeline` | **composite**: product + components + their versions (one call for the Constellation view) |
| GET | `/products/{id}/components` | list components |
| POST | `/components` | create `{product_id, name, kind}` (`kind`: library\|service\|ui\|cli) |
| GET | `/components/{id}/versions` | version history (immutable) |
| POST | `/versions` | create `{component_id, version, prerelease?}` |
| POST | `/versions/{id}/rollback` | mark `rolled_back`, re-activate previous (no delete) |
| GET | `/products/{id}/releases` | release ledger |
| POST | `/products/{id}/releases` | **cut a release** (see §5) |
| GET | `/releases/{id}` | a release + frozen manifest |
| GET | `/products/{id}/events` | **SSE** live stream (see §6) |
| GET | `/health` · `/ready` | liveness / readiness (Helm probes) |

### Core schemas

```jsonc
// Product
{ "id": "uuid", "name": "Aurora Platform", "description": "…", "created_at": "ISO-8601" }

// Component
{ "id": "uuid", "product_id": "uuid", "name": "lavs-api", "kind": "service" }

// Version (immutable)
{ "id": "uuid", "component_id": "uuid",
  "major": 2, "minor": 4, "patch": 0, "prerelease": null,
  "status": "active",            // active | superseded | rolled_back
  "created_at": "ISO-8601" }

// Release (frozen)
{ "id": "uuid", "product_id": "uuid",
  "product_version": "5.1.0",    // server-assigned, see §5
  "label": "Aurora 5.1",         // optional human label
  "created_at": "ISO-8601",
  "components": [
    { "component_id": "uuid", "name": "lavs-api", "version_id": "uuid", "version": "2.4.0" }
  ] }

// timeline (composite response for the Constellation view)
{ "product": { …Product },
  "components": [ { …Component, "versions": [ …Version ] } ] }
```

### Error model (uniform)

```jsonc
{ "error": { "code": "validation_error", "message": "human readable", "details": { … } } }
```

| HTTP | code | when |
|------|------|------|
| 401 | `unauthorized` | no/invalid credential |
| 403 | `forbidden` / `domain_not_allowed` | not permitted |
| 404 | `not_found` | unknown id |
| 409 | `conflict` | duplicate (name, email, etc.) |
| 422 | `validation_error` | bad body (e.g. non-semver version) |

## 4. Version semantics

- Versions are **append-only and immutable**; `version` must match `^\d+\.\d+\.\d+$`
  (optionally `-prerelease`). Server rejects others with `422 validation_error`.
- "Patch" is just a new version with `patch+1` on the same component — no special table.
- **Rollback** (`POST /versions/{id}/rollback`) sets the current `active` version to
  `rolled_back` and re-activates the prior version. History is never deleted.

## 5. Cut Release — the write that matters

`POST /products/{id}/releases`

```jsonc
// request — NO version, NO manifest (server owns both)
{ "label": "Aurora 5.1", "notes": "optional" }
// optional header: Idempotency-Key: <uuid>   (prevents double-cut)
```

Server behavior:
1. Snapshot each component's current **`active`** version.
2. **Auto-increment** the product version (server-owned counter; **default bump = minor**,
   starting from the product's configured base). The client **cannot** set the version —
   only an optional `label`.
3. Persist an immutable `Release` + `release_components` pinning the exact `version_id`s.
4. Emit a `release.cut` event on the SSE stream (§6).

```mermaid
sequenceDiagram
    participant UI
    participant API
    participant DB
    UI->>API: POST /products/{id}/releases {label?}  (+Idempotency-Key)
    API->>DB: select active version per component
    API->>API: product_version = bump_minor(current)
    API->>DB: insert Release + release_components (immutable)
    API-->>UI: 201 {Release with frozen manifest, product_version}
    API-->>UI: SSE event: release.cut
```

Because versions are immutable and the release pins `version_id`s, **a cut release never
changes** even if components ship new versions or get rolled back afterward — it's a
permanent, reproducible statement of the product composition.

## 6. Live updates (SSE)

`GET /products/{id}/events` — `text/event-stream`. Server→client only; all writes stay REST.
(WebSocket is a possible future upgrade if bidirectional needs appear; SSE is sufficient now.)

```jsonc
event: version.created
data: { "component_id":"uuid", "version": { …Version } }

event: version.rolled_back
data: { "component_id":"uuid", "version_id":"uuid", "reactivated_version_id":"uuid" }

event: release.cut
data: { "release": { …Release } }
```

FE handling: append a new **star** on `version.created`, dim/strike on `version.rolled_back`,
add a **ledger** entry on `release.cut`. The meridian + product-version derivation remain a
pure **client-side projection** over this data.

## 7. The Constellation view's data lifecycle

```mermaid
sequenceDiagram
    participant UI
    participant API
    UI->>API: GET /auth/me  (gate)
    UI->>API: GET /products/{id}/timeline   (components + versions, one call)
    UI->>API: GET /products/{id}/releases   (ledger)
    UI->>API: open SSE /products/{id}/events
    Note over UI: meridian position & pinned set are derived client-side
    UI->>API: POST /products/{id}/releases (on "Cut")
    API-->>UI: 201 + SSE release.cut
```

## 8. Cross-cutting / config

- **Base URL:** FE reads `VITE_LAVS_API_URL`; one build runs against any backend.
- **CORS:** backend allow-list (`LAVS_CORS_ORIGINS`); credentials enabled for the session cookie.
- **Environments:** identical API on **DuckDB (local/default)** and **PostgreSQL (prod)**.
- **Edition flag:** `GET /health` (or a `/meta`) reports `edition` + enabled `auth_modes` so
  the UI renders the right login (password form vs Stytch widget vs "configured key").
- **API versioning:** prefix `/// v1` once contracts stabilize.

## 9. Open items

- Domain allow-list source (env list vs DB-managed) and email-send transport.
- Session store backend (in-DuckDB vs Redis) for multi-replica prod.
- Idempotency-Key retention window.
- Org/RBAC model (deferred) — how products map to orgs/teams.
- Whether `/products/{id}/timeline` needs pagination for very long histories.
