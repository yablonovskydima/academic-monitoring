from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_shared.claims import Claims, InvalidTokenError, Role, decode_and_verify

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
