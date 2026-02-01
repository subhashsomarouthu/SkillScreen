"""
Admin Controller for Interview Service

Provides cross-organization visibility for platform administrators.
All endpoints require 'admin' role authentication.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from jose import jwt, JWTError
import os
import sys

sys.path.append("/common-service")
from db import UnitOfWork

router = APIRouter(prefix="/admin", tags=["Admin"])

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


class InterviewItem(BaseModel):
    id: str
    organization_id: str
    candidate_id: Optional[str]
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    status: str
    created_at: Optional[str]


class InterviewListResponse(BaseModel):
    interviews: List[InterviewItem]
    total_count: int


class CandidateItem(BaseModel):
    id: str
    full_name: Optional[str]
    email: str
    organization_id: str
    created_at: Optional[str]


class CandidateListResponse(BaseModel):
    candidates: List[CandidateItem]
    total_count: int


class DashboardStats(BaseModel):
    total_interviews: int
    completed_interviews: int
    in_progress_interviews: int
    scheduled_interviews: int
    total_organizations: int
    total_candidates: int


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

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: TokenData = Depends(require_admin)
):
    """
    Get platform-wide interview statistics.
    
    **Admin Only** - Returns aggregate stats about interviews.
    """
    try:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            
            # Count interviews by status
            status_counts = uow.session.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM interviews 
                GROUP BY status
            """))
            counts_by_status = {row.status: row.count for row in status_counts}
            
            # Total interviews
            total_interviews = sum(counts_by_status.values())
            
            # Count unique organizations
            org_count = uow.session.execute(text("""
                SELECT COUNT(DISTINCT organization_id) as count 
                FROM interviews
            """)).scalar()
            
            # Count unique candidates
            candidate_count = uow.session.execute(text("""
                SELECT COUNT(DISTINCT candidate_id) as count 
                FROM interviews 
                WHERE candidate_id IS NOT NULL
            """)).scalar()
            
            return {
                "success": True,
                "data": {
                    "total_interviews": total_interviews,
                    "completed_interviews": counts_by_status.get("completed", 0),
                    "in_progress_interviews": counts_by_status.get("in_progress", 0),
                    "scheduled_interviews": counts_by_status.get("scheduled", 0) + counts_by_status.get("pending", 0),
                    "total_organizations": org_count or 0,
                    "total_candidates": candidate_count or 0
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/interviews")
async def get_all_interviews(
    current_user: TokenData = Depends(require_admin),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get all interviews in the platform.
    
    **Admin Only** - Returns all interviews with optional filtering.
    """
    try:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            
            # Build query with optional filters
            query_str = """
                SELECT 
                    i.id, i.organization_id, i.candidate_id, i.status, i.created_at,
                    c.full_name as candidate_name, c.email as candidate_email
                FROM interviews i
                LEFT JOIN candidates c ON i.candidate_id = c.id
                WHERE 1=1
            """
            params = {}
            
            if organization_id:
                query_str += " AND i.organization_id = :org_id"
                params["org_id"] = organization_id
            
            if status:
                query_str += " AND i.status = :status"
                params["status"] = status
            
            query_str += " ORDER BY i.created_at DESC"
            
            result = uow.session.execute(text(query_str), params)
            interviews = [dict(row._mapping) for row in result]
            
            # Paginate
            total_count = len(interviews)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated = interviews[start_idx:end_idx]
            
            interview_items = [
                {
                    "id": str(i.get("id", "")),
                    "organization_id": str(i.get("organization_id", "")),
                    "candidate_id": str(i.get("candidate_id")) if i.get("candidate_id") else None,
                    "candidate_name": i.get("candidate_name"),
                    "candidate_email": i.get("candidate_email"),
                    "status": i.get("status", ""),
                    "created_at": str(i.get("created_at", "")) if i.get("created_at") else None
                }
                for i in paginated
            ]
            
            return {
                "success": True,
                "data": {
                    "interviews": interview_items,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get interviews: {str(e)}")


@router.get("/candidates")
async def get_all_candidates(
    current_user: TokenData = Depends(require_admin),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get all candidates in the platform.
    
    **Admin Only** - Returns all candidates with optional filtering.
    """
    try:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            
            # Build query with optional filters
            query_str = """
                SELECT id, full_name, email, organization_id, created_at
                FROM candidates
                WHERE 1=1
            """
            params = {}
            
            if organization_id:
                query_str += " AND organization_id = :org_id"
                params["org_id"] = organization_id
            
            query_str += " ORDER BY created_at DESC"
            
            result = uow.session.execute(text(query_str), params)
            candidates = [dict(row._mapping) for row in result]
            
            # Paginate
            total_count = len(candidates)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated = candidates[start_idx:end_idx]
            
            candidate_items = [
                {
                    "id": str(c.get("id", "")),
                    "full_name": c.get("full_name"),
                    "email": c.get("email", ""),
                    "organization_id": str(c.get("organization_id", "")),
                    "created_at": str(c.get("created_at", "")) if c.get("created_at") else None
                }
                for c in paginated
            ]
            
            return {
                "success": True,
                "data": {
                    "candidates": candidate_items,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get candidates: {str(e)}")
