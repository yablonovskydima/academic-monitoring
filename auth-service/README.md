# Auth Service

Identity, authentication, and role/scope assignment for the academic-monitoring platform. Issues the JWTs every other service trusts (via `auth-shared`), and owns who's allowed to curate which groups or oversee which faculties.

## Roles

One role per user (`UserRoleEnum` / `auth_shared.Role`): `admin`, `dean`, `curator`. Public self-registration (`/auth/register`) always creates a `curator` — elevated roles are only ever set by an admin (see `UserService.create`'s `role` field, used directly, not through `/auth/register`).

Every admin-granting endpoint is itself admin-only, so the very first admin can't come from the API — `bootstrap.py`'s `bootstrap_admin()` runs on every app startup (from `main.py`'s `lifespan`, right after `init_db()`) and creates one directly in the database if `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are set. It's idempotent — if a user with that email already exists (admin or otherwise), it's left untouched and returned as-is, so this is safe to leave configured across every restart. Unset either variable and it's a no-op.

- **curator** — self-assigns to groups they oversee (`/curator-assignments`), scoped by ownership on delete.
- **dean** — assigned to a faculty by an admin (`/dean-assignments`), not self-service — a dean's scope is a whole faculty, which warrants more oversight than a curator claiming a group they already know is theirs. Can read their own faculty list; admin can read anyone's.
- **admin** — everything gated by `require_role(...)`: (de)activating users, dean assignment, reading the audit log.

Every role-gated endpoint uses `dependencies.require_role`, *not* `auth_shared.require_role` directly. The difference matters: `auth_shared.require_role` only verifies the JWT signature/expiry — it never touches the database, so it can't tell a deactivated user's still-valid token from an active one. `dependencies.require_role` is built on top of `get_current_user`, which re-reads the user and checks `is_active` on every single call. That's deliberate — it's what makes deactivating a user (or an admin) take effect immediately instead of waiting up to `ACCESS_TOKEN_EXPIRE_MINUTES` for the old token to expire. `auth_shared.require_role` stays as-is for future consumers (e.g. the BFF) that don't own the users table and have no DB to check against.

## Auth flow

Stateless short-lived access tokens (JWT, ~15 min, see `auth-shared`) + stateful long-lived refresh tokens (random string, only the hash stored in the DB, revocable, rotated on every use). See `services/auth_service.py` for the full orchestration: register, login, refresh, logout, revoke-all-sessions, change-password, and a forgot/reset-password flow (the reset token mechanism is real — only the email-sending step is a stub, logged to stdout with a `TODO` for when `notification-service` exists).

Every sensitive action writes to `audit_log` — see `models/audit_log.py`'s docstring and the root `CLAUDE.md` before adding business logic that reads sensitive data or changes another user's access.

## Rate limiting

Every `/auth/*` endpoint (see `rate_limit.py`) is behind an in-memory, fixed-window rate limiter, keyed differently depending on the caller:

- **No valid access token** (register, login, refresh, logout, forgot/reset-password — the truly public, brute-forceable surface) — limited per client IP, `RATE_LIMIT_UNAUTHENTICATED_MAX` requests per `RATE_LIMIT_WINDOW_SECONDS` (default `10`/`60s`).
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

`import-service` must be running and reachable at `IMPORT_SERVICE_URL` before creating curator/dean assignments (they're validated against it).

## API

- `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` — public
- `GET /auth/me`, `POST /auth/revoke-all` (kill every session for the caller), `POST /auth/change-password` — any authenticated, active user
- `POST /auth/forgot-password` + `POST /auth/reset-password` — public, token-based (see Auth flow above)
- `POST /users/{id}/activate`, `/deactivate` — admin-only
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
- `test_auth_flow.py` — register, login (success/failure/inactive user), refresh rotation + reuse rejection, logout, revoke-all, change-password (+ session revocation), forgot/reset-password (+ token single-use), `/auth/me`.
- `test_rbac.py` — every role-gated endpoint: correct role succeeds, wrong role gets 403, ownership checks (curator assignment delete, dean self-vs-other faculty read) are enforced.
- `test_deactivation_revokes_access.py` — the scenario the RBAC security review was about: a user (including an admin) deactivated mid-session loses access on their very next request, even though their access token hasn't expired yet.
- `test_rate_limit.py` — `InMemoryRateLimiter` unit tests (limit enforcement, `retry_after` value, window reset, per-key isolation, `reset()`) with an injected fake clock, plus HTTP-level tests that an anonymous caller gets blocked with a `429` + `Retry-After` after `RATE_LIMIT_UNAUTHENTICATED_MAX` requests, and that an authenticated caller isn't affected by that same IP bucket.
- `test_bootstrap.py` — `bootstrap_admin()` is a no-op without env vars, creates an admin when configured, is idempotent on repeat calls, and doesn't touch an existing non-admin user that already holds the configured email.

### Known gaps (not covered by the above, flagged during the security review, not yet fixed)

- `UserService.authenticate` has a timing side-channel: an unknown login returns instantly, a known one with a wrong password waits on a real bcrypt check.
- `/auth/register`'s 409 ("Email already registered") lets an attacker enumerate registered emails; `/auth/login` and `/auth/forgot-password` are already generic on purpose.
- `UserService.set_active` doesn't stop an admin from deactivating themselves (or the last remaining admin).
