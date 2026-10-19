"""API dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.security.auth import decode_access_token
from app.security.acl import User

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Extract user info from token
    user = User(
        user_id=payload.get("sub"),
        tenant_id=payload.get("tenant_id"),
        department=payload.get("department"),
        role_level=payload.get("role_level"),
    )

    return user
