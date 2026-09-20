# auth-shared

A small internal library (not a service — no FastAPI app, no database) for verifying JWT access tokens issued by `auth-service`. Any service that needs to know who's calling and what role/scope they have imports this instead of re-implementing JWT verification.

## Why this exists

`auth-service` is the only thing that *issues* tokens (it owns the signing key logic in its own `security.py`). Every other service only ever needs to *verify* them — decode the token, confirm the signature and expiry, and read the claims. That verification logic is identical everywhere it's needed, so it lives here once instead of being copied into each consumer.

## What's in it

- **`Claims`** — a typed model of what's inside a verified token: `user_id`, `role`, `group_ids`, `faculty_ids`.
- **`Role`** — enum of the platform's roles (`admin`, `dean`, `curator`).
- **`decode_and_verify(token) -> Claims`** — verifies signature + expiry, raises `InvalidTokenError` otherwise.
- **`get_claims`** — a FastAPI dependency that pulls the token from the `Authorization: Bearer` header and returns `Claims`, or a 401.
- **`require_role(*roles)`** — a dependency factory: `Depends(require_role(Role.admin))` returns `Claims` if the caller has one of the given roles, otherwise a 403.

## Usage

```python
from auth_shared import Claims, Role, require_role
from fastapi import Depends

@router.post("/something-sensitive")
def do_something(claims: Claims = Depends(require_role(Role.admin))):
    ...
```

## Config

Reads `JWT_SECRET_KEY` (required) and `JWT_ALGORITHM` (default `HS256`) from the repo root `.env` — the same values `auth-service` signs tokens with. There's nothing to run or deploy separately; it's just installed as a workspace dependency (`uv add --package <consumer> auth-shared`).
