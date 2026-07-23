# Stytch Manual Smoke (EE) — live-tenant verification

The manual smoke procedure promised by P6 **G-P6b**: the automated suites verify the Stytch
lane only at the provider boundary (an injected fake verifier — no network), so this
walkthrough is the one place the EE flow is exercised against a **real Stytch consumer
project**. Run it by hand before an EE release, and whenever the Stytch SDK (`stytch` on the
backend, `@stytch/vanilla-js` on the frontend) is upgraded.

Time: ~20 minutes. Requires a browser, a real inbox you control, and a Stytch account.

See also: [API_CONTRACT.md §1–2](../design/API_CONTRACT.md) ·
[P6 plan](../planning/P6_MULTIAGENT_EXECUTION_PLAN.md) (G-P6b, G-P6e).

---

## 1. Prerequisites

1. **A Stytch *Consumer* project** (not B2B), in its **Test** environment.
2. In the Stytch dashboard, enable the products the widget is hard-configured for
   (a fixed product decision — G-P6e; the list is not deploy-configurable):
   - **Email magic links**
   - **OAuth** with the **Google** and **GitHub** providers configured
3. **Redirect URLs allow-listed.** The frontend passes its own current page URL
   (`window.location.href`) as both `loginRedirectURL` and `signupRedirectURL` for magic
   links *and* OAuth. Allow-list the frontend origin's login URL for both the **Login** and
   **Sign-up** redirect types — for the dev walk below that is `http://localhost:5173/`.
4. Collect the three credentials from *Project settings → API keys*:
   - Project ID (`project-test-…`)
   - Secret (`secret-test-…`)
   - Public token (publishable, `public-token-test-…`)
5. Local toolchain per the repo baseline: `uv` (backend, Python 3.14) and `pnpm`
   (frontend, `frontend/ui`).

## 2. Environment

Export before booting the backend (all read on demand by
`app/auth/auth_settings.py`):

| Variable | Required | Value / notes |
|---|---|---|
| `LAVS_EDITION` | ✅ | `ee`. The `stytch` mode is **edition-gated**: on `oss` (the default) a `stytch` token in `LAVS_AUTH_MODES` is silently ignored. |
| `LAVS_AUTH_MODES` | ✅ | `stytch` for a pure-EE walk. Combinations are valid — e.g. `stytch,password` or `stytch,password,apikey` — and the login page then renders both the password form and the Stytch widget. Note: `apikey` is additionally auto-enabled (and reported by `/meta`) whenever `LAVS_API_KEY` is set, even if not listed. |
| `LAVS_STYTCH_PROJECT_ID` | ✅ | The Stytch project ID. |
| `LAVS_STYTCH_SECRET` | ✅ | The Stytch project secret. Read on demand, handed only to the SDK client, never logged. |
| `LAVS_STYTCH_PUBLIC_TOKEN` | ✅* | The publishable public token. Surfaced browser-safely as `stytch_public_token` on `GET /meta` — the preferred path. *Alternative:* bake `VITE_STYTCH_PUBLIC_TOKEN` into the frontend build instead; the UI prefers `/meta` and falls back to the build-time value. |
| `LAVS_ALLOWED_EMAIL_DOMAINS` | optional | Comma list; empty/unset means all domains allowed. Leave unset for the happy path; used in negative check 5.3. |
| `LAVS_SESSION_TTL_SECONDS` | optional | Session/cookie lifetime; defaults to `604800` (7 days). |

```bash
export LAVS_EDITION=ee
export LAVS_AUTH_MODES=stytch
export LAVS_STYTCH_PROJECT_ID='project-test-…'
export LAVS_STYTCH_SECRET='secret-test-…'
export LAVS_STYTCH_PUBLIC_TOKEN='public-token-test-…'
```

## 3. Boot

Backend (repo root; DuckDB is the default backend, file `app/test.db`):

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Frontend, either dev or built:

```bash
cd frontend/ui
pnpm install
pnpm dev            # serves http://localhost:5173, proxies API calls to :8001
# — or built —
pnpm build && pnpm preview   # allow-list the preview origin's URL in Stytch instead
```

The Vite dev server proxies API requests to the backend
(`VITE_LAVS_API_URL`, default `http://127.0.0.1:8001`), so the walk is same-origin and no
CORS setup is needed.

> **Browser note:** the `lavs_session` cookie is set with the `Secure` attribute. Chrome and
> Firefox accept `Secure` cookies from `http://localhost`; Safari does not — use
> Chrome/Firefox for this walk, or front the stack with HTTPS.

## 4. The walk (happy path)

Use a fresh email address that has **never** signed up in this LAVS database.

### 4.1 `/meta` reports EE + stytch (+ token)

```bash
curl -s http://127.0.0.1:8001/meta
```

Expect:

```json
{"edition": "ee", "auth_modes": ["stytch"], "stytch_public_token": "public-token-test-…"}
```

`stytch_public_token` appears only when the mode is enabled **and** the token is configured;
extra modes (e.g. `apikey`) appear if enabled.

### 4.2 Login page renders the widget

Open `http://localhost:5173`. Unauthenticated, you land on the sign-in screen; with
`LAVS_AUTH_MODES=stytch` it renders the **“Managed sign-in”** section and mounts Stytch's
prebuilt widget (the SDK is lazy-loaded — a brief “Loading managed sign-in…” is normal). The
widget offers **email magic link** plus **Google** and **GitHub** OAuth buttons.

If you instead see *“no Stytch publishable token is configured”*, `/meta` returned no token
and no `VITE_STYTCH_PUBLIC_TOKEN` was baked in — fix §2 and reload.

### 4.3 Authenticate via magic link or OAuth

- **Magic link:** enter the test email → open the inbox → click the link. It redirects back
  to the login page; the remounted widget authenticates the token from the URL.
- **OAuth:** click Google or GitHub → complete the provider's consent → redirected back.

Either way, on flow completion the frontend exchanges the Stytch session credential at the
backend — no manual step.

### 4.4 Callback exchange sets the hardened cookie

The exchange is `POST /auth/stytch/callback` with body `{"stytch_token": "…"}` (the session
JWT when available, else the opaque session token). Verify in the browser dev tools
(Network tab) that the response is **200** with a user body, and carries:

```
Set-Cookie: lavs_session=…; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

You should now be in the app (the Constellation UI), signed in.

### 4.5 `/auth/me` returns the mapped user

Still in dev tools (or by navigating with the cookie present):

```
GET /auth/me → 200
{"id": "<ULID>", "email": "<your test email, lower-cased>", "status": "active", "edition": "ee"}
```

### 4.6 A Stytch-born user row exists — active, with an unusable password hash

The callback maps the Stytch-verified email onto the shared `users` table, created `active`
on first sight with a **random, unusable** argon2 hash (Stytch-born users can never
authenticate through `/auth/login`). Inspect the row (stop the backend first, or copy the
file — DuckDB is single-writer):

```bash
uv run python -c "
import duckdb
conn = duckdb.connect('app/test.db', read_only=True)
row = conn.execute(
    'SELECT id, email, status, edition, password_hash FROM users WHERE email = ?',
    ['<your test email>'],
).fetchone()
print(row)
"
```

Expect: `status = 'active'`, `edition = 'ee'`, and a `password_hash` beginning `$argon2` (a
real hash — of a random secret nobody knows). Cross-check the unusability: with `password`
also in `LAVS_AUTH_MODES`, `POST /auth/login` for that email with any password returns the
generic 401.

## 5. Negative checks

Every failure below must be the **same generic 401**, envelope
`{"error": {"code": "unauthorized", "message": "invalid credentials", …}}` — no path may
reveal *why* (no user/config enumeration).

### 5.1 OSS mode: callback answers 401

Restart the backend with `LAVS_EDITION=oss` (or unset), keeping `LAVS_AUTH_MODES=stytch` and
the Stytch credentials in place:

- `GET /meta` → `{"edition": "oss", "auth_modes": []}` — the `stytch` token is ignored
  outside `ee`, and no `stytch_public_token` is exposed.
- `POST /auth/stytch/callback` with **any** token — even a currently valid one — returns
  the generic 401 (indistinguishable from a bad credential):

```bash
curl -si -X POST http://127.0.0.1:8001/auth/stytch/callback \
  -H 'Content-Type: application/json' -d '{"stytch_token": "anything"}'
```

Restore the EE env afterwards.

### 5.2 Garbage / unverified-email tokens: 401

- **Garbage token** (EE env): the same `curl` as above with a made-up token → 401. The
  backend log notes only the Stytch error class/status — never the token.
- **Stytch user with no verified email:** the verifier surfaces only a **verified** email;
  an identity without one fails closed with the same 401. To exercise this against a live
  tenant, mint a session for a Stytch user whose email is unverified (e.g. create the user
  and session through Stytch's *Test*-environment backend API without completing email
  verification) and POST that token to the callback → 401. If you cannot construct such a
  session, note it as *not exercised* — magic-link and OAuth flows inherently verify the
  email, which is exactly the property being protected.
- An **omitted/empty** `stytch_token` is a **422** (malformed request), not a 401.

### 5.3 Domain allow-list enforced on the Stytch lane

Restart the backend with the EE env **plus** `LAVS_ALLOWED_EMAIL_DOMAINS=example.com` (any
domain that does **not** match your test email):

- Complete a fresh magic-link/OAuth flow → the callback returns the generic 401 (not
  signup's 403 — a distinct status would let a probe fingerprint the allow-list).
- This applies to the **already-mapped** user from §4 too (defense in depth): tightening the
  allow-list locks out existing out-of-domain users; they are not grandfathered in.

Unset the variable and confirm the §4 login works again.

## 6. Teardown

1. Stop the frontend (`Ctrl-C` on `pnpm dev`/`preview`) and the backend uvicorn.
2. Remove the smoke user row (or delete the throwaway `app/test.db` entirely if this was a
   scratch database):

   ```bash
   uv run python -c "
   import duckdb
   conn = duckdb.connect('app/test.db')
   conn.execute('DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = ?)', ['<your test email>'])
   conn.execute('DELETE FROM users WHERE email = ?', ['<your test email>'])
   conn.close()
   "
   ```

3. In the Stytch dashboard (Test environment): revoke active sessions and delete the test
   user(s) created by the walk.
4. Unset the env vars (`unset LAVS_STYTCH_SECRET …`); the secret must not linger in shell
   history or profiles. Rotate the Test-environment secret if there is any doubt.

## 7. Recording the result

Record pass/fail per step (4.1–4.6, 5.1–5.3) with the date, Stytch SDK versions
(`stytch` from `uv.lock`, `@stytch/vanilla-js` from `frontend/ui/pnpm-lock.yaml`), and the
browser used, in the release notes or the tracking issue for the EE cut.
