from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth_shared import Claims, Role, get_claims, require_role
from auth_shared.config import JWT_ALGORITHM, JWT_SECRET_KEY

app = FastAPI()


@app.get("/whoami")
def whoami(claims: Claims = Depends(get_claims)):
    return {"user_id": claims.user_id, "role": claims.role.value}


@app.get("/admin-only")
def admin_only(claims: Claims = Depends(require_role(Role.admin))):
    return {"user_id": claims.user_id}


@app.get("/staff")
def staff(claims: Claims = Depends(require_role(Role.admin, Role.dean))):
    return {"role": claims.role.value}


client = TestClient(app)


def token_for(role: str, user_id: int = 1, expires_in: timedelta = timedelta(minutes=5), type: str = "access") -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": type, "exp": now + expires_in},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_get_claims_returns_the_verified_claims():
    response = client.get("/whoami", headers=bearer(token_for("dean", user_id=9)))

    assert response.status_code == 200
    assert response.json() == {"user_id": 9, "role": "dean"}


def test_missing_authorization_header_is_rejected():
    assert client.get("/whoami").status_code in (401, 403)


def test_garbage_token_is_401():
    response = client.get("/whoami", headers=bearer("not-a-jwt"))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_non_bearer_scheme_is_rejected():
    response = client.get("/whoami", headers={"Authorization": f"Basic {token_for('admin')}"})

    assert response.status_code in (401, 403)


def test_require_role_lets_the_allowed_role_through():
    response = client.get("/admin-only", headers=bearer(token_for("admin", user_id=5)))

    assert response.status_code == 200
    assert response.json() == {"user_id": 5}


@pytest.mark.parametrize("role", ["dean", "curator"])
def test_require_role_forbids_other_roles(role):
    response = client.get("/admin-only", headers=bearer(token_for(role)))

    assert response.status_code == 403


def test_require_role_with_an_invalid_token_is_401_not_403():
    assert client.get("/admin-only", headers=bearer("nope")).status_code == 401


@pytest.mark.parametrize("role,expected", [("admin", 200), ("dean", 200), ("curator", 403)])
def test_require_role_accepts_any_of_several_roles(role, expected):
    assert client.get("/staff", headers=bearer(token_for(role))).status_code == expected
