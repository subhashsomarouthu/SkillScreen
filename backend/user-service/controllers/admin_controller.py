"""
Admin Controller for User Service

Provides cross-organization visibility for platform administrators.
All endpoints require 'admin' role authentication.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from jose import jwt, JWTError
import os


from db import UnitOfWork
from utilities.logger import init_logger

router = APIRouter(prefix="/admin", tags=["Admin"])
log = init_logger("user-service-admin")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
security = HTTPBearer()


# ==========================================
# PYDANTIC MODELS
# ==========================================

class TokenData(BaseModel):
    user_id: str
    email: str
    organization_id: str
    role: str


class OrganizationItem(BaseModel):
    id: str
    name: str
    domain: Optional[str]
    has_coding_access: bool
    created_at: Optional[str]


class UpdateOrganizationRequest(BaseModel):
    has_coding_access: Optional[bool] = None


class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationItem]
    total_count: int


class UserItem(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    organization_id: str
    is_active: bool
    created_at: Optional[str]


class UserListResponse(BaseModel):
    users: List[UserItem]
    total_count: int


# ==========================================
# AUTH DEPENDENCY
# ==========================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Decode and validate JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            organization_id=payload.get("organization_id"),
            role=payload.get("role")
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_admin(current_user: TokenData = Depends(get_current_user)):
    """Authorization middleware to protect admin routes"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only admin users can access this resource"
        )
    return current_user


# ==========================================
# ADMIN ENDPOINTS
# ==========================================

@router.get("/organizations", response_model=OrganizationListResponse)
async def get_all_organizations(
    current_user: TokenData = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get all organizations in the platform.
    
    **Admin Only** - Returns all organizations across the platform.
    """
    try:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            
            query = text("""
                SELECT id, name, domain, has_coding_access, created_at 
                FROM organizations 
                ORDER BY created_at DESC
            """)
            
            result = uow.session.execute(query)
            orgs = [dict(row._mapping) for row in result]
            
            # Paginate
            total_count = len(orgs)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_orgs = orgs[start_idx:end_idx]
            
            org_items = [
                OrganizationItem(
                    id=str(org.get("id", "")),
                    name=org.get("name", ""),
                    domain=org.get("domain"),
                    has_coding_access=org.get("has_coding_access", False),
                    created_at=str(org.get("created_at", "")) if org.get("created_at") else None
                )
                for org in paginated_orgs
            ]
            
            return OrganizationListResponse(
                organizations=org_items,
                total_count=total_count
            )
            
    except Exception as e:
        import traceback
        error_msg = f"Failed to get organizations: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        log.error(error_msg)
        raise HTTPException(status_code=500, detail=f"Failed to get organizations: {str(e)}")


@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    current_user: TokenData = Depends(require_admin),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    role: Optional[str] = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get all users in the platform.
    
    **Admin Only** - Returns all users with optional filtering.
    """
    try:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            
            # Build query with optional filters
            query_str = """
                SELECT id, email, first_name, last_name, role, organization_id, is_active, created_at 
                FROM users 
                WHERE 1=1
            """
            params = {}
            
            if organization_id:
                query_str += " AND organization_id = :org_id"
                params["org_id"] = organization_id
            
            if role:
                query_str += " AND role = :role"
                params["role"] = role
            
            query_str += " ORDER BY created_at DESC"
            
            result = uow.session.execute(text(query_str), params)
            users = [dict(row._mapping) for row in result]
            
            # Paginate
            total_count = len(users)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_users = users[start_idx:end_idx]
            
            user_items = [
                UserItem(
                    id=str(user.get("id", "")),
                    email=user.get("email", ""),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                    role=user.get("role", ""),
                    organization_id=str(user.get("organization_id", "")),
                    is_active=user.get("is_active", True),
                    created_at=str(user.get("created_at", "")) if user.get("created_at") else None
                )
                for user in paginated_users
            ]
            
            return UserListResponse(
                users=user_items,
                total_count=total_count
            )
            
    except Exception as e:
        log.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")


@router.get("/stats")
async def get_platform_stats(
    current_user: TokenData = Depends(require_admin)
):
    """
    Get platform-wide statistics.
    
    **Admin Only** - Returns aggregate stats for the platform.
    """
    try:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            
            # Count organizations
            org_count = uow.session.execute(text("SELECT COUNT(*) as count FROM organizations")).scalar()
            
            # Count users by role
            user_stats = uow.session.execute(text("""
                SELECT role, COUNT(*) as count 
                FROM users 
                GROUP BY role
            """))
            role_counts = {row.role: row.count for row in user_stats}
            
            # Total users
            total_users = sum(role_counts.values())
            
            return {
                "success": True,
                "data": {
                    "total_organizations": org_count,
                    "total_users": total_users,
                    "users_by_role": role_counts
                }
            }
            
    except Exception as e:
        log.error(f"Failed to get platform stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.patch("/organizations/{org_id}")
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    current_user: TokenData = Depends(require_admin)
):
    """
    Update an organization's settings.
    
    **Admin Only** - Currently supports toggling 'has_coding_access'.
    """
    try:
        from repositories.user_repository import UserRepository
        
        with UnitOfWork() as uow:
            repo = UserRepository(uow)
            
            updates = {}
            if request.has_coding_access is not None:
                updates["has_coding_access"] = request.has_coding_access
            
            if not updates:
                raise HTTPException(status_code=400, detail="No updates provided")
            
            updated_org = repo.update_organization(org_id, **updates)
            
            if not updated_org:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            return {
                "success": True, 
                "message": "Organization updated successfully",
                "data": updated_org
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to update organization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update organization: {str(e)}")
