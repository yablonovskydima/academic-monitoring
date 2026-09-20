# Auth Service

Identity, authentication, and role/scope assignment for the academic-monitoring platform. Issues the JWTs every other service trusts (via `auth-shared`), and owns who's allowed to curate which groups or oversee which faculties.

## Roles

One role per user (`UserRoleEnum` / `auth_shared.Role`): `admin`, `dean`, `curator`. Public self-registration (`/auth/register`) always creates a `curator` — elevated roles are only ever set by an admin (see `UserService.create`'s `role` field, used directly, not through `/auth/register`). There is currently no bootstrap path for the very first admin — it has to be inserted directly (e.g. via `UserService.create(..., role=UserRoleEnum.admin)` from a shell), since every admin-granting endpoint is itself admin-only.

- **curator** — self-assigns to groups they oversee (`/curator-assignments`), scoped by ownership on delete.
- **dean** — assigned to a faculty by an admin (`/dean-assignments`), not self-service — a dean's scope is a whole faculty, which warrants more oversight than a curator claiming a group they already know is theirs. Can read their own faculty list; admin can read anyone's.
- **admin** — everything gated by `require_role(...)`: (de)activating users, dean assignment, reading the audit log.

Every role-gated endpoint uses `dependencies.require_role`, *not* `auth_shared.require_role` directly. The difference matters: `auth_shared.require_role` only verifies the JWT signature/expiry — it never touches the database, so it can't tell a deactivated user's still-valid token from an active one. `dependencies.require_role` is built on top of `get_current_user`, which re-reads the user and checks `is_active` on every single call. That's deliberate — it's what makes deactivating a user (or an admin) take effect immediately instead of waiting up to `ACCESS_TOKEN_EXPIRE_MINUTES` for the old token to expire. `auth_shared.require_role` stays as-is for future consumers (e.g. the BFF) that don't own the users table and have no DB to check against.

## Auth flow

Stateless short-lived access tokens (JWT, ~15 min, see `auth-shared`) + stateful long-lived refresh tokens (random string, only the hash stored in the DB, revocable, rotated on every use). See `services/auth_service.py` for the full orchestration: register, login, refresh, logout, revoke-all-sessions, change-password, and a forgot/reset-password flow (the reset token mechanism is real — only the email-sending step is a stub, logged to stdout with a `TODO` for when `notification-service` exists).

Every sensitive action writes to `audit_log` — see `models/audit_log.py`'s docstring and the root `CLAUDE.md` before adding business logic that reads sensitive data or changes another user's access.

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

### Known gaps (not covered by the above, flagged during the security review, not yet fixed)

- No rate limiting or lockout on `/auth/login` — brute-forceable.
- `UserService.authenticate` has a timing side-channel: an unknown login returns instantly, a known one with a wrong password waits on a real bcrypt check.
- `/auth/register`'s 409 ("Email already registered") lets an attacker enumerate registered emails; `/auth/login` and `/auth/forgot-password` are already generic on purpose.
- `UserService.set_active` doesn't stop an admin from deactivating themselves (or the last remaining admin).
