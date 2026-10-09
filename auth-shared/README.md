# auth-shared

A small internal library (not a service — no FastAPI app, no database) for verifying JWT access tokens issued by `auth-service`. Any service that needs to know who's calling and what role/scope they have imports this instead of re-implementing JWT verification.

## Why this exists

`auth-service` is the only thing that *issues* tokens (it creates them in its own `utils/security.py`). Every other service only ever needs to *verify* them — decode the token, confirm the signature and expiry, and read the claims. That verification logic is identical everywhere it's needed, so it lives here once instead of being copied into each consumer.

## What's in it

- **`Claims`** — a typed model of what's inside a verified token: `user_id`, `role`, `group_ids`, `faculty_ids`, and `session_id` (the `sid` claim, `None` for tokens without one).
- **`Role`** — enum of the platform's roles (`admin`, `dean`, `curator`).
- **`decode_and_verify(token) -> Claims`** — verifies signature + expiry, raises `InvalidTokenError` otherwise.
- **`get_claims`** — a FastAPI dependency that pulls the token from the `Authorization: Bearer` header and returns `Claims`, or a 401.
- **`get_verified_claims`** / **`require_verified_role(*roles)`** — the same, but instead of trusting the token they ask `auth-service` (`GET {AUTH_SERVICE_URL}/auth/introspect`) and return its current answer: live role, live `group_ids`/`faculty_ids`, and a 401 for a deactivated user, a deleted account or a revoked session. A token that fails the local signature check never leaves the process. If `auth-service` is unreachable or answers anything other than 200/401 the dependency returns 503.
- **`AuthEvent`** — names of the events `auth-service` publishes when sessions or scopes change (see "Events" in `auth-service/README.md`); the contract between the publisher and every consumer.
- **`require_role(*roles)`** — a dependency factory: `Depends(require_role(Role.admin))` returns `Claims` if the caller has one of the given roles, otherwise a 403.

## Which one to use

`get_claims` / `require_role` are stateless: they check signature, expiry and token type, never a database or the network. So they cannot know that a user was deactivated or deleted, that their role or assignments changed, or that the session behind a token was revoked (refresh, logout, revoke-all, password change): such a token is honoured until it expires (15 minutes by default), and `group_ids`/`faculty_ids` are the values at issue time. They are fine for cheap, low-risk checks.

`get_verified_claims` / `require_verified_role` cost one HTTP request to `auth-service` per call (no caching yet, deliberately: any cache would bring the staleness back) and are the ones to use for anything that reads sensitive student data or changes something. Inside `auth-service` itself the equivalent is `dependencies.get_current_user` / `require_role`, which read the database directly.

TODO: once `auth-service` publishes `AuthEvent`s to RabbitMQ, `get_verified_claims` should cache introspection results and invalidate them on those events instead of asking `auth-service` on every request.

Tokens are signed with one shared HS256 secret, so any consumer that can verify tokens could also forge them.

## Usage

```python
from auth_shared import Claims, Role, require_role
from fastapi import Depends

@router.post("/something-sensitive")
def do_something(claims: Claims = Depends(require_role(Role.admin))):
    ...
```

## Config

Reads `JWT_SECRET_KEY` (required) and `JWT_ALGORITHM` (default `HS256`) from the repo root `.env`, plus `AUTH_SERVICE_URL` (base URL of `auth-service`, e.g. `http://localhost:8003`; only needed by consumers of the verified dependencies, a missing value is a `RuntimeError` on first use) — the same values `auth-service` signs tokens with. There's nothing to run or deploy separately; it's just installed as a workspace dependency (`uv add --package <consumer> auth-shared`).

## Tests

```bash
uv run pytest auth-shared/tests
```

They don't depend on `auth-service`: `test_claims.py` covers `decode_and_verify` (valid token, scopes/session defaults, expired, wrong secret, other algorithm, unsigned `alg=none`, non-access type, malformed payload, garbage) and `test_dependencies.py` covers `get_claims` and `require_role` through a throwaway FastAPI app (401 vs 403, one or several allowed roles, non-Bearer scheme), and `test_verified_dependencies.py` covers the introspecting variants against a faked `auth-service` (claims come from the authority, the token is forwarded, 401 vs 503 mapping, garbage tokens never leave the process, missing URL). The real round trip against `auth-service` is tested in `auth-service/tests/test_introspection.py`.
