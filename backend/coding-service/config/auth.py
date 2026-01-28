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


class CandidateTokenData(BaseModel):
    """Token data for candidates (may have limited info from interview token)"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    organization_id: Optional[str] = None
    role: str = "candidate"
    is_candidate: bool = True


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


async def get_current_user_or_candidate(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData | CandidateTokenData:
    """
    Dependency that accepts either:
    1. A valid JWT token (returns TokenData)
    2. An interview token for candidates (returns CandidateTokenData)

    Use this for endpoints that both recruiters and candidates can access.
    """
    try:
        token = credentials.credentials

        # Try to decode as JWT first
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )

            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            organization_id: str = payload.get("organization_id")
            role: str = payload.get("role")

            if all([user_id, email, organization_id, role]):
                return TokenData(
                    user_id=user_id,
                    email=email,
                    organization_id=organization_id,
                    role=role,
                    first_name=payload.get("first_name"),
                    last_name=payload.get("last_name")
                )
        except JWTError:
            pass  # Not a valid JWT, might be an interview token

        # If JWT decode failed, assume it's a candidate interview token
        # Interview tokens are simple strings validated elsewhere
        # For candidate endpoints, we just need to verify a token exists
        if token and len(token) > 10:  # Basic check for non-empty token
            return CandidateTokenData(
                role="candidate",
                is_candidate=True
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
