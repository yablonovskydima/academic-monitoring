# Auth Service

Identity, authentication, and role/scope assignment for the academic-monitoring platform. Issues the JWTs every other service trusts (via `auth-shared`), and owns who's allowed to curate which groups or oversee which faculties.

## Roles

One role per user (`UserRoleEnum` / `auth_shared.Role`): `admin`, `dean`, `curator`. There is no public self-registration: accounts are created only by an admin (`POST /users/`), who picks the role, and their profile data (name, email) can only be changed by an admin (`PATCH /users/{id}`) — users can't edit their own, so nobody can rename themselves. Emails must belong to `ALLOWED_EMAIL_DOMAINS` (default `pnu.edu.ua,cnu.edu.ua`; empty value disables the check). `login` is always the part of the email before `@`, so changing the email changes the login too (the old login stops working immediately, the new one is sent to the new address via `notifications.send_login_changed`; existing sessions survive, since tokens carry the user id, not the login). Limits: the derived login must pass the login rules (3-50 chars, letters/digits/`.`/`_`/`-`) and must not belong to anyone else — otherwise the whole edit is rejected with 409. Because two domains are allowed, `ivan@pnu.edu.ua` and `ivan@cnu.edu.ua` collide on login, so one of them can't exist at the same time. A freed login can later be taken by someone else; the audit log is keyed by user id, so history stays attributed correctly.

The admin sets the initial password in the request body; it is "emailed" to the user — until `notification-service` exists that's `notifications.send_account_credentials`, which prints the email, login and the raw password to the service console. Sending a plaintext password is a stopgap; the intended replacement is a one-time link. A forgotten or leaked password goes through the normal forgot/reset flow.

Every admin-granting endpoint is itself admin-only, so the very first admin can't come from the API — `bootstrap.py`'s `bootstrap_admin()` runs on every app startup (from `main.py`'s `lifespan`, right after `init_db()`) and creates one directly in the database if `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are set. It's idempotent — if a user with that email already exists (admin or otherwise), it's left untouched and returned as-is, so this is safe to leave configured across every restart. Unset either variable and it's a no-op.

- **curator** — self-assigns to groups they oversee (`/curator-assignments`), scoped by ownership on delete.
- **dean** — assigned to a faculty by an admin (`/dean-assignments`), not self-service — a dean's scope is a whole faculty, which warrants more oversight than a curator claiming a group they already know is theirs. Can read their own faculty list; admin can read anyone's.
- **admin** — everything gated by `require_role(...)`: (de)activating users, changing roles, dean assignment, reading the audit log.

Every role-gated endpoint uses `dependencies.require_role`, *not* `auth_shared.require_role` directly. The difference matters: `auth_shared.require_role` only verifies the JWT signature/expiry — it never touches the database, so it can't tell a deactivated user's still-valid token from an active one. `dependencies.require_role` is built on top of `get_current_user`, which re-reads the user and checks `is_active` on every single call. That's deliberate — it's what makes deactivating a user (or an admin) take effect immediately instead of waiting up to `ACCESS_TOKEN_EXPIRE_MINUTES` for the old token to expire. `auth_shared.require_role` stays as-is for future consumers (e.g. the BFF) that don't own the users table and have no DB to check against.

## Auth flow

Short-lived access tokens (JWT, ~15 min, see `auth-shared`) + stateful long-lived refresh tokens (random string, only the hash stored in the DB, revocable, rotated on every use). Each access token carries a `sid` claim — the id of the refresh-token row it was issued with — and `get_current_user` checks that row is still unrevoked and unexpired. So refreshing, logging out, revoke-all, change/reset-password all kill the matching access tokens immediately, not after `ACCESS_TOKEN_EXPIRE_MINUTES`. The cost is one extra DB read per authenticated request; `auth_shared`'s own `get_claims`/`require_role` stay stateless and don't see this, so a consumer without access to the users/sessions DB (the future BFF) will still honour such a token until it expires. See `services/auth_service.py` for the full orchestration: login, refresh, logout, revoke-all-sessions, change-password, and a forgot/reset-password flow (the reset token mechanism is real — only the email-sending step is a stub: `notifications.send_password_reset` prints the email, login and token to the service console until `notification-service` exists).

Every sensitive action writes to `audit_log` — see `models/audit_log.py`'s docstring and the root `CLAUDE.md` before adding business logic that reads sensitive data or changes another user's access.

## Rate limiting

Every `/auth/*` endpoint (see `utils/rate_limit.py`) is behind an in-memory, fixed-window rate limiter, keyed differently depending on the caller:

- **No valid access token** (login, refresh, logout, forgot/reset-password — the truly public, brute-forceable surface) — limited per client IP, `RATE_LIMIT_UNAUTHENTICATED_MAX` requests per `RATE_LIMIT_WINDOW_SECONDS` (default `10`/`60s`).
- **Valid access token** (`/me`, `/revoke-all`, `/change-password`, or any `/auth/*` call made with a still-valid token) — limited per `user_id` instead of per IP, `RATE_LIMIT_AUTHENTICATED_MAX` requests per window (default `60`/`60s`) — deliberately more generous, since a known authenticated caller isn't the brute-force threat this exists to stop.

Exceeding the limit raises `RateLimitExceeded` (a custom exception, not a bare `HTTPException`), caught by a handler registered in `main.py` that returns `429` with a `Retry-After` header and a generic JSON body — no detail about which bucket or key tripped it.

This is in-process, in-memory state — correct for a single instance, not shared across replicas. If/when this service runs behind more than one process, the bucket store needs to move to something shared (Redis, most likely) instead of `InMemoryRateLimiter`'s in-memory dict.

## Stack

FastAPI + SQLAlchemy + PostgreSQL + `auth-shared` (JWT verification) + `bcrypt` (password hashing) + `httpx` (validates `group_id`/`faculty_id` against `import-service` before creating an assignment). Tests run against SQLite in-memory, not PostgreSQL — see Tests below.

## Setup

1. Start the database (from the repo root):
   ```bash
   docker compose up -d postgres-auth
   ```
2. Env vars this service reads (see repo root `.env`):
   - `DB_USER_AUTH_SERVICE`, `DB_PASSWORD_AUTH_SERVICE`, `DB_HOST_AUTH_SERVICE`, `DB_PORT_AUTH_SERVICE`, `DB_NAME_AUTH_SERVICE`
   - `IMPORT_SERVICE_URL` — base URL of `import-service` (required, used to validate group/faculty assignments)
   - `AUTH_SERVICE_PORT` (default `8003`)
   - `JWT_SECRET_KEY` (required), `JWT_ALGORITHM` (default `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (default `15`)
   - `REFRESH_TOKEN_EXPIRE_DAYS` (default `30`), `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` (default `30`)
   - `RATE_LIMIT_WINDOW_SECONDS` (default `60`), `RATE_LIMIT_UNAUTHENTICATED_MAX` (default `10`), `RATE_LIMIT_AUTHENTICATED_MAX` (default `60`) — see Rate limiting above
   - `ALLOWED_EMAIL_DOMAINS` (comma-separated, default `pnu.edu.ua,cnu.edu.ua`) — checked when an admin creates a user or edits an email; the bootstrap admin is exempt
   - `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` (both unset by default — bootstrap is skipped), `INITIAL_ADMIN_FIRST_NAME` / `INITIAL_ADMIN_LAST_NAME` (default `Admin`/`Admin`) — see Roles above
3. Install dependencies (from the repo root, `uv` workspace):
   ```bash
   uv sync --all-packages
   ```
   (`uv sync` alone only syncs the root project and will *uninstall* the other members' editable installs — see root `CLAUDE.md`.)
4. Run the service:
   ```bash
   uv run auth-service
   ```
   or `uvicorn auth_service.main:app --reload --port 8003`.

`import-service` must be running and reachable at `IMPORT_SERVICE_URL` before creating curator/dean assignments (they're validated against it). If it's down or answers with an error, `ImportServiceClient` raises `ImportServiceUnavailable` and the app returns `503` instead of a 500.

## API

- `POST /auth/login`, `/auth/refresh`, `/auth/logout` — public
- `POST /users/` `{first_name, last_name, email, password, role}` — admin-only; creates the account, emails (console stub) the credentials. 409 on duplicate email or login, 422 on a disallowed email domain or weak password
- `PATCH /users/{id}` `{first_name?, last_name?, email?}` — admin-only; at least one field, same validation, login follows the email (see Roles), old/new values audited (`user_updated`)
- `GET /auth/me`, `POST /auth/revoke-all` (kill every session for the caller), `POST /auth/change-password` — any authenticated, active user
- `POST /auth/forgot-password` + `POST /auth/reset-password` — public, token-based (see Auth flow above)
- `POST /users/{id}/activate`, `/deactivate` — admin-only; an admin can't deactivate themselves (400)
- `POST /users/{id}/role` `{"role": "admin|dean|curator"}` — admin-only; an admin can't change their own role (400). A role change revokes all of the target's sessions, deletes their curator/dean assignments (they belong to the old role), and is audited (`user_role_changed`, with from/to)
- `POST /curator-assignments/`, `GET /curator-assignments/me` — curator role required
- `DELETE /curator-assignments/{id}` — curator role required, and only the assignment's own owner
- `POST /dean-assignments/`, `DELETE /dean-assignments/{id}` — admin-only
- `GET /dean-assignments/{user_id}` — admin or dean role required; a dean may only query their own `user_id`, admin may query any
- `GET /audit-log/`, `/audit-log/by-user/{id}`, `/audit-log/by-target/{type}/{id}` — admin-only

## Tests

`auth-service/tests/` — run from the repo root:
```bash
uv run pytest auth-service/tests
```
No live database needed: `conftest.py` overrides `get_db` with a fresh in-memory SQLite database per test (`StaticPool`, so it survives across the threadpool FastAPI's `TestClient` runs endpoints in), and the `ImportServiceClient` calls used by assignment creation are monkeypatched rather than hitting a real `import-service`.

- `test_validators.py` — pure unit tests for name/login/password-strength rules.
- `test_user_creation.py` — public `/auth/register` is gone; admin-only user creation (allowed domains, duplicate email/login, weak password, credentials printed, audited) and admin-only profile editing (validation, audit with old/new values, no self-edit).
- `test_auth_flow.py` — login (success/failure/inactive user), refresh rotation + reuse rejection, logout, revoke-all, change-password (+ session revocation), forgot/reset-password (+ token single-use), `/auth/me`.
- `test_rbac.py` — every role-gated endpoint: correct role succeeds, wrong role gets 403, ownership checks (curator assignment delete, dean self-vs-other faculty read) are enforced.
- `test_auth_flow.py` also covers session binding: a refresh, logout or revoke-all invalidates the previous access tokens right away.
- `test_deactivation_revokes_access.py` — the scenario the RBAC security review was about: a user (including an admin) deactivated mid-session loses access on their very next request, even though their access token hasn't expired yet.
- `test_rate_limit.py` — `InMemoryRateLimiter` unit tests (limit enforcement, `retry_after` value, window reset, per-key isolation, `reset()`) with an injected fake clock, plus HTTP-level tests that an anonymous caller gets blocked with a `429` + `Retry-After` after `RATE_LIMIT_UNAUTHENTICATED_MAX` requests, and that an authenticated caller isn't affected by that same IP bucket.
- `test_user_admin.py` — admin can't deactivate or re-role themselves; role change is admin-only, 404/422 on bad input, revokes the target's sessions, clears their old assignments and is audited.
- `test_import_service_down.py` — assignment creation returns 503 (not 500) when `import-service` refuses the connection or answers 5xx.
- `test_bootstrap.py` — `bootstrap_admin()` is a no-op without env vars, creates an admin when configured, is idempotent on repeat calls, and doesn't touch an existing non-admin user that already holds the configured email.

### Known gaps (not covered by the above, flagged during the security review, not yet fixed)
- New accounts get their raw password by (console-stubbed) email, and there is no forced password change on first login.