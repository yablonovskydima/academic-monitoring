import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_shared.claims import Claims, InvalidTokenError, Role, decode_and_verify
from auth_shared.config import AUTH_SERVICE_URL

_bearer_scheme = HTTPBearer()

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permission to perform this action",
)


_AUTH_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Authentication service is unavailable",
)


def get_claims(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> Claims:
    try:
        return decode_and_verify(credentials.credentials)
    except InvalidTokenError:
        raise _INVALID_TOKEN


def require_role(*roles: Role):
    def dependency(claims: Claims = Depends(get_claims)) -> Claims:
        if claims.role not in roles:
            raise _FORBIDDEN
        return claims

    return dependency


def get_verified_claims(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    _local_check: Claims = Depends(get_claims),
) -> Claims:
    if not AUTH_SERVICE_URL:
        raise RuntimeError("AUTH_SERVICE_URL is not set. Check your .env file.")

    try:
        response = httpx.get(
            f"{AUTH_SERVICE_URL}/auth/introspect",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
            timeout=5.0,
        )
    except httpx.HTTPError:
        raise _AUTH_UNAVAILABLE

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise _INVALID_TOKEN
    if response.status_code != status.HTTP_200_OK:
        raise _AUTH_UNAVAILABLE

    return Claims.model_validate(response.json())


def require_verified_role(*roles: Role):
    def dependency(claims: Claims = Depends(get_verified_claims)) -> Claims:
        if claims.role not in roles:
            raise _FORBIDDEN
        return claims

    return dependency
