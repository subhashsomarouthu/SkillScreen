from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Optional
from config.settings import settings


# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Decoded JWT token data"""
    user_id: str
    email: str
    organization_id: str
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to extract and validate JWT token.
    Returns TokenData with user_id, email, organization_id, and role.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        organization_id: str = payload.get("organization_id")
        role: str = payload.get("role")

        if not all([user_id, email, organization_id, role]):
            raise credentials_exception

        return TokenData(
            user_id=user_id,
            email=email,
            organization_id=organization_id,
            role=role,
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name")
        )

    except JWTError:
        raise credentials_exception


def require_role(*allowed_roles: str):
    """
    Dependency factory to require specific roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: TokenData = Depends(require_role("recruiter"))):
            ...
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
