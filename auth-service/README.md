# Auth Service

Identity, authentication, and role/scope assignment for the academic-monitoring platform. Issues the JWTs every other service trusts (via `auth-shared`), and owns who's allowed to curate which groups or oversee which faculties.

## Roles

One role per user (`UserRoleEnum` / `auth_shared.Role`): `admin`, `dean`, `curator`. There is no public self-registration: accounts are created only by an admin (`POST /users/`), who picks the role, and their profile data (name, email) can only be changed by an admin (`PATCH /users/{id}`) — users can't edit their own, so nobody can rename themselves. Emails must belong to `ALLOWED_EMAIL_DOMAINS` (default `pnu.edu.ua,cnu.edu.ua`; empty value disables the check). `login` is always the part of the email before `@`, so changing the email changes the login too (the old login stops working immediately, the new one is sent to the new address via `notifications.send_login_changed`; existing sessions survive, since tokens carry the user id, not the login). Limits: the derived login must pass the login rules (3-50 chars, letters/digits/`.`/`_`/`-`) and must not belong to anyone else — otherwise the whole edit is rejected with 409. Because two domains are allowed, `ivan@pnu.edu.ua` and `ivan@cnu.edu.ua` collide on login, so one of them can't exist at the same time. A freed login can later be taken by someone else; the audit log is keyed by user id, so history stays attributed correctly.

The admin sets the initial password in the request body; it is "emailed" to the user — until `notification-service` exists that's `notifications.send_account_credentials`, which prints the email, login and the raw password to the service console. Sending a plaintext password is a stopgap; the intended replacement is a one-time link. A forgotten or leaked password goes through the normal forgot/reset flow.

Every admin-granting endpoint is itself admin-only, so the very first admin can't come from the API — `bootstrap.py`'s `bootstrap_admin()` runs on every app startup (from `main.py`'s `lifespan`, right after `init_db()`) and creates one directly in the database if `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are set. It's idempotent — if a user with that email already exists (admin or otherwise), it's left untouched and returned as-is, so this is safe to leave configured across every restart. Unset either variable and it's a no-op.

- **curator** — self-assigns to groups they oversee (`/curator-assignments`), scoped by ownership on delete.
- **dean** — assigned to a faculty by an admin (`/dean-assignments`), not self-service — a dean's scope is a whole faculty, which warrants more oversight than a curator claiming a group they already know is theirs. Can read their own faculty list; admin can read anyone's.
- **admin** — everything gated by `require_role(...)`: creating, editing, (de)activating, re-roling and deleting users, dean assignment, reading the audit log. Deleting a user removes the account, their sessions, reset tokens and assignments in one go; the `audit_log` is never touched — it has no foreign key to `users`, their old entries keep the id, and a `user_deleted` entry stores a snapshot (login, email, name, role) so that id can still be resolved later. Their login and email become free again.

Every role-gated endpoint uses `dependencies.require_role`, *not* `auth_shared.require_role` directly. The difference matters: `auth_shared.require_role` only verifies the JWT signature/expiry — it never touches the database, so it can't tell a deactivated user's still-valid token from an active one. `dependencies.require_role` is built on top of `get_current_user`, which re-reads the user and checks `is_active` on every single call. That's deliberate — it's what makes deactivating a user (or an admin) take effect immediately instead of waiting up to `ACCESS_TOKEN_EXPIRE_MINUTES` for the old token to expire. `auth_shared.require_role` stays as-is for future consumers (e.g. the BFF) that don't own the users table and have no DB to check against.

## Auth flow

Short-lived access tokens (JWT, ~15 min, see `auth-shared`) + stateful long-lived refresh tokens (random string, only the hash stored in the DB, revocable, rotated on every use). Each access token carries a `sid` claim — the id of the refresh-token row it was issued with — and `get_current_user` checks that row is still unrevoked and unexpired. So refreshing, logging out, revoke-all, change/reset-password all kill the matching access tokens immediately, not after `ACCESS_TOKEN_EXPIRE_MINUTES`. The cost is one extra DB read per authenticated request; `auth_shared`'s `get_claims`/`require_role` stay stateless and don't see this, so a consumer without access to the users/sessions DB (the future BFF) would honour such a token until it expires. Consumers that need the same guarantee (anything reading sensitive data) use `auth_shared.get_verified_claims` / `require_verified_role` instead: they call `GET /auth/introspect` here, which re-reads the user, the session and the current assignments and answers with fresh `role`/`group_ids`/`faculty_ids`, or 401. See `services/auth_service.py` for the full orchestration: login, refresh, logout, revoke-all-sessions, change-password, and a forgot/reset-password flow (the reset token mechanism is real — only the email-sending step is a stub: `notifications.send_password_reset` prints the email, login and token to the service console until `notification-service` exists).

Every sensitive action writes to `audit_log` — see `models/audit_log.py`'s docstring and the root `CLAUDE.md` before adding business logic that reads sensitive data or changes another user's access.

## Rate limiting

One app-level dependency (`FastAPI(dependencies=[Depends(rate_limit)])` in `main.py`, implementation in `utils/rate_limit.py`) covers every endpoint of every router, current and future — nothing has to be added per router or per endpoint. Only `/health` is exempt (probes would otherwise trip it). The limiter is in-memory, fixed-window (`RATE_LIMIT_WINDOW_SECONDS`, default `60`), and every request is counted against two buckets:

- **Per IP, for everyone** — `RATE_LIMIT_IP_MAX` requests per window (default `300`). It is deliberately high: a whole university can sit behind one NAT address. It stops a single address from spraying many accounts or tokens.
- **Per identity** — a valid access token is limited per `user_id` (`RATE_LIMIT_AUTHENTICATED_MAX`, default `60`); a request without one is limited per anonymous IP (`RATE_LIMIT_UNAUTHENTICATED_MAX`, default `10`), which is what slows down login/forgot-password brute force. The anonymous and per-IP buckets are separate, so authenticated traffic never eats an anonymous visitor's budget.

`/auth/introspect` skips the per-IP bucket, because a gateway calls it for every user request from a single address; the per-user bucket still applies to it. The budgets are shared across all endpoints (60 requests a minute per user in total, not per route). Exceeding any bucket raises `RateLimitExceeded` (a custom exception), handled in `main.py`: `429`, a `Retry-After` header and a generic JSON body that doesn't say which bucket tripped. Expired buckets are swept out of memory at most once per window, so the dictionary doesn't grow with every IP ever seen.

State is per-process: correct for a single instance, not shared across replicas. Behind a reverse proxy `request.client.host` is the proxy's address unless uvicorn runs with `--forwarded-allow-ips`. If one route ever needs a stricter limit than the global one, add a second dependency on that route with its own key prefix.

## Events (stub, RabbitMQ is TODO)

Every change that makes an issued token or a consumer's cached claims out of date goes through `utils/events.py` (`publish_event(event, payload)`). The names are a shared contract, `auth_shared.AuthEvent`. Events are published after the database change has been committed, and nothing is published when the operation is rejected.

| event | payload | published when |
|---|---|---|
| `auth.user.deactivated` | `user_id` | an admin deactivates a user (activation publishes nothing) |
| `auth.user.deleted` | `user_id` | an admin deletes a user |
| `auth.user.role_changed` | `user_id`, `old_role`, `new_role` | an admin changes a role (assignments are wiped, see Roles) |
| `auth.user.scopes_changed` | `user_id` | a curator group or dean faculty assignment is created or removed |
| `auth.session.revoked` | `user_id`, `session_id` (`null` = every session of the user) | refresh (old session), logout, revoke-all, change/reset password, role change |

Right now `publish_event` only prints `[event] <name> <payload>` to the service console.

TODO:
- Replace the print with a real RabbitMQ publisher (suggestion: a durable topic exchange `auth.events`, routing key = event name). Only `publish_event` changes, the call sites stay. If delivery must be guaranteed, add a transactional outbox, because the publish currently happens after the commit and a broker outage would lose the event.
- Consumer side, in `auth-shared`: until events flow, `get_verified_claims` asks `/auth/introspect` on every request. Once they do, it should cache introspection results locally and drop entries on these events (by `user_id`; by `session_id` for `auth.session.revoked`, or every entry of the user when it is `null`). The cache also needs a safety max age in case an event is missed.

## Stack

FastAPI + SQLAlchemy + PostgreSQL + `auth-shared` (JWT verification) + `bcrypt` (password hashing) + `httpx` (validates `group_id`/`faculty_id` against `import-service` before creating an assignment). Tests run against SQLite in-memory, not PostgreSQL — see Tests below.

## Setup

1. Start the database (from the repo root):
   ```bash
   docker compose up -d postgres-auth
   ```
2. Env vars this service reads (copy the repo root `.env.example` to `.env` and fill it in; it lists every variable of every service, required ones first and optional ones with their defaults):
   - `DB_USER_AUTH_SERVICE`, `DB_PASSWORD_AUTH_SERVICE`, `DB_HOST_AUTH_SERVICE`, `DB_PORT_AUTH_SERVICE`, `DB_NAME_AUTH_SERVICE`
   - `IMPORT_SERVICE_URL` — base URL of `import-service` (required, used to validate group/faculty assignments)
   - `AUTH_SERVICE_PORT` (default `8003`)
   - `JWT_SECRET_KEY` (required), `JWT_ALGORITHM` (default `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (default `15`)
   - `REFRESH_TOKEN_EXPIRE_DAYS` (default `30`), `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` (default `30`)
   - `RATE_LIMIT_WINDOW_SECONDS` (default `60`), `RATE_LIMIT_UNAUTHENTICATED_MAX` (default `10`), `RATE_LIMIT_AUTHENTICATED_MAX` (default `60`), `RATE_LIMIT_IP_MAX` (default `300`) — see Rate limiting above
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

Schema note: `audit_log.user_id` no longer has a foreign key to `users` (so deleting a user never touches the audit trail). A database created before that change still has the old constraint; recreate it once (`docker compose down -v`, then `up -d postgres-auth` again; the bootstrap admin is recreated on start), otherwise deleting a user who has audit entries fails. Tests run on SQLite with foreign keys switched on, which reuses freed ids; PostgreSQL sequences do not.

## API

- `POST /auth/login`, `/auth/refresh`, `/auth/logout` — public
- `GET /users/` (filters `role`, `is_active`; `limit` ≤ 500, `offset`) and `GET /users/{id}` — admin-only
- `POST /users/` `{first_name, last_name, email, password, role}` — admin-only; creates the account, emails (console stub) the credentials. 409 on duplicate email or login, 422 on a disallowed email domain or weak password
- `PATCH /users/{id}` `{first_name?, last_name?, email?}` — admin-only; at least one field, same validation, login follows the email (see Roles), old/new values audited (`user_updated`)
- `GET /auth/introspect` — current claims of the caller, read from the database (for `auth_shared.get_verified_claims`); 401 for a deactivated user, a revoked session or a deleted account
- `GET /auth/me`, `POST /auth/revoke-all` (kill every session for the caller), `POST /auth/change-password` — any authenticated, active user
- `POST /auth/forgot-password` + `POST /auth/reset-password` — public, token-based (see Auth flow above)
- `DELETE /users/{id}` — admin-only; an admin can't delete themselves (400); audited (`user_deleted`, with a snapshot)
- `POST /users/{id}/activate`, `/deactivate` — admin-only; an admin can't deactivate themselves (400)
- `POST /users/{id}/role` `{"role": "admin|dean|curator"}` — admin-only; an admin can't change their own role (400). A role change revokes all of the target's sessions, deletes their curator/dean assignments (they belong to the old role), and is audited (`user_role_changed`, with from/to)
- `POST /curator-assignments/`, `GET /curator-assignments/me` — curator role required
- `DELETE /curator-assignments/{id}` — curator role required, and only the assignment's own owner; audited (`curator_group_assignment_removed`)
- `POST /dean-assignments/`, `DELETE /dean-assignments/{id}` — admin-only; both audited (`dean_faculty_assignment_removed` on delete)
- `GET /dean-assignments/{user_id}` — admin or dean role required; a dean may only query their own `user_id`, admin may query any
- `GET /audit-log/`, `/audit-log/by-user/{id}`, `/audit-log/by-target/{type}/{id}` — admin-only; all take `limit` (1-500, default 100) and `offset`, newest first

## Tests

`auth-service/tests/` — run from the repo root:
```bash
uv run pytest auth-service/tests
```
No live database needed: `conftest.py` overrides `get_db` with a fresh in-memory SQLite database per test (`StaticPool`, so it survives across the threadpool FastAPI's `TestClient` runs endpoints in), and the `ImportServiceClient` calls used by assignment creation are monkeypatched rather than hitting a real `import-service`.

- `test_validators.py` — pure unit tests for name/login/password-strength rules.
- `test_user_creation.py` — public `/auth/register` is gone; admin-only user creation (allowed domains, duplicate email/login, weak password, credentials printed, audited) and admin-only profile editing (validation, audit with old/new values, no self-edit).
- `test_auth_flow.py` — login (success/failure/inactive user, failed attempts audited with the client IP), refresh rotation + reuse rejection, logout, revoke-all, change-password (+ session revocation), forgot/reset-password (+ token single-use, token handed to the notifications stub), `/auth/me`, and session binding: a refresh, logout or revoke-all invalidates the previous access tokens right away.
- `test_rbac.py` — every role-gated endpoint: correct role succeeds, wrong role gets 403, ownership checks (curator assignment delete, dean self-vs-other faculty read) are enforced.
- `test_deactivation_revokes_access.py` — the scenario the RBAC security review was about: a user (including an admin) deactivated mid-session loses access on their very next request, even though their access token hasn't expired yet.
- `test_rate_limit.py` — `InMemoryRateLimiter` unit tests with an injected fake clock (limit, `retry_after`, window reset, per-key isolation, `reset()`, expired buckets swept from memory), plus HTTP-level tests: every router's endpoints are limited, `/health` is exempt, anonymous and authenticated traffic use separate buckets, users have independent buckets, and authenticated users are still capped per IP.
- `test_user_admin.py` — admin can't deactivate or re-role themselves; role change is admin-only, 404/422 on bad input, revokes the target's sessions, clears their old assignments and is audited.
- `test_import_service_down.py` — assignment creation returns 503 (not 500) when `import-service` refuses the connection or answers 5xx.
- `test_user_listing.py` — admin-only list/get of users, role and activity filters, pagination and its cap.
- `test_assignment_removal.py` — successful curator/dean assignment removal and its audit entries, 404s, duplicate/wrong-role/unknown-group rejections.
- `test_audit_pagination_and_clock.py` — audit-log page-size cap and pagination; refresh and reset token expiry are computed in UTC.
- `test_user_deletion.py` — deleting a user removes tokens and assignments, kills their access at once, keeps their audit history, writes a snapshot, frees login/email, can't delete yourself; SQLite foreign keys are switched on in `conftest.py` so this behaves like PostgreSQL.
- `test_introspection.py` — `/auth/introspect` returns fresh claims, rejects revoked/invalid tokens and skips the IP bucket; a mini consumer app wired to this service through `auth_shared` shows that verified claims see new assignments, deactivation, revoked sessions and role changes that the stateless ones miss.
- `test_events.py` — every state change above publishes exactly the documented event (and nothing when the request is rejected), checked with a captured `publish_event`.
- `test_bootstrap.py` — `bootstrap_admin()` is a no-op without env vars, creates an admin when configured, is idempotent on repeat calls, and doesn't touch an existing non-admin user that already holds the configured email.

### Known gaps (flagged in reviews, not fixed yet)
Not implemented
- Real email delivery (`notification-service`), CORS (not needed until a browser talks to this service directly).
