from datetime import datetime, timedelta, timezone

import jwt
import pytest

from auth_shared import Claims, InvalidTokenError, Role, decode_and_verify
from auth_shared.config import JWT_ALGORITHM, JWT_SECRET_KEY


def make_token(secret: str = JWT_SECRET_KEY, algorithm: str = JWT_ALGORITHM, **overrides) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "42",
        "role": "curator",
        "group_ids": [1, 2],
        "faculty_ids": [],
        "sid": 7,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not None or k == "sid"}
    return jwt.encode(payload, secret, algorithm=algorithm)


def test_valid_token_is_decoded_into_claims():
    claims = decode_and_verify(make_token())

    assert claims == Claims(user_id=42, role=Role.curator, group_ids=[1, 2], faculty_ids=[], session_id=7)


def test_scopes_default_to_empty_lists_and_session_to_none():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": "1", "role": "admin", "type": "access", "exp": now + timedelta(minutes=5)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    claims = decode_and_verify(token)

    assert claims.group_ids == []
    assert claims.faculty_ids == []
    assert claims.session_id is None


@pytest.mark.parametrize("role", ["admin", "dean", "curator"])
def test_every_known_role_is_accepted(role):
    assert decode_and_verify(make_token(role=role)).role == Role(role)


def test_expired_token_is_rejected():
    expired = datetime.now(timezone.utc) - timedelta(seconds=1)

    with pytest.raises(InvalidTokenError):
        decode_and_verify(make_token(exp=expired))


def test_token_signed_with_another_secret_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_and_verify(make_token(secret="not-the-real-secret-but-long-enough-for-hs256"))


def test_token_with_a_different_algorithm_is_rejected():
    forged = make_token(algorithm="HS512")

    with pytest.raises(InvalidTokenError):
        decode_and_verify(forged)


def test_unsigned_token_is_rejected():
    payload = {"sub": "1", "role": "admin", "type": "access"}
    unsigned = jwt.encode(payload, key=None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_and_verify(unsigned)


def test_non_access_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_and_verify(make_token(type="refresh"))


def test_token_without_a_type_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_and_verify(make_token(type=None))


@pytest.mark.parametrize("overrides", [
    {"sub": None},
    {"sub": "not-a-number"},
    {"role": None},
    {"role": "superuser"},
])
def test_malformed_payload_is_rejected(overrides):
    now = datetime.now(timezone.utc)
    payload = {"sub": "42", "role": "curator", "type": "access", "exp": now + timedelta(minutes=5)}
    for key, value in overrides.items():
        if value is None:
            payload.pop(key)
        else:
            payload[key] = value
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    with pytest.raises((InvalidTokenError, ValueError)):
        decode_and_verify(token)


def test_garbage_is_rejected():
    for garbage in ("", "abc", "a.b.c"):
        with pytest.raises(InvalidTokenError):
            decode_and_verify(garbage)
