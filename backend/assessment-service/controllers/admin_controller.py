"""
Admin Controller for Assessment Service

Provides cross-organization visibility for platform administrators.
All endpoints require 'admin' role authentication.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import sys
sys.path.append('/common-service')
from db import UnitOfWork
from repositories.assessment_repository import AssessmentRepository
from config.auth import get_current_user, require_role, TokenData
from config.logger import logger


router = APIRouter(prefix="/v1/admin", tags=["Admin Dashboard"])


# ==========================================
# RESPONSE MODELS
# ==========================================

class OrganizationStats(BaseModel):
    """Statistics for a single organization"""
    organization_id: str
    total_interviews: int = 0
    completed_interviews: int = 0
    assessed_count: int = 0
    pending_assessment: int = 0
    average_score: Optional[float] = None
    hire_count: int = 0
    no_hire_count: int = 0


class PlatformStats(BaseModel):
    """Platform-wide statistics"""
    total_organizations: int
    total_interviews: int
    total_assessments: int
    completed_interviews: int
    pending_assessments: int
    average_overall_score: Optional[float]
    recommendation_breakdown: Dict[str, int]


class AssessmentItem(BaseModel):
    """Assessment item for admin listing"""
    id: str
    interview_id: str
    candidate_id: Optional[str]
    organization_id: str
    overall_score: float
    recommendation: str
    technical_score: Optional[float]
    communication_score: Optional[float]
    soft_skills_score: Optional[float]
    proctoring_risk_score: Optional[float]
    created_at: str


class AdminAssessmentListResponse(BaseModel):
    """Response for admin assessment list"""
    assessments: List[AssessmentItem]
    total_count: int
    page: int
    page_size: int


class AdminStatsResponse(BaseModel):
    """Response for admin dashboard stats"""
    platform: PlatformStats
    organizations: List[OrganizationStats]


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def require_admin(current_user: TokenData = Depends(get_current_user)):
    """Authorization middleware to protect admin routes"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only admin users can access this resource"
        )
    return current_user


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/dashboard/stats", response_model=AdminStatsResponse)
async def get_admin_dashboard_stats(
    current_user: TokenData = Depends(require_admin)
):
    """
    Get platform-wide statistics for admin dashboard.
    
    **Admin Only** - Returns cross-organization statistics including:
    - Total interviews, assessments, and organizations
    - Recommendation breakdown (hire/no-hire/maybe)
    - Per-organization statistics
    """
    try:
        with UnitOfWork() as uow:
            repo = AssessmentRepository(uow.session)
            
            # Get all assessments across all organizations
            all_assessments = repo.get_all_assessments()
            
            # Calculate platform-wide stats
            total_assessments = len(all_assessments)
            
            # Group by organization
            org_stats_map: Dict[str, OrganizationStats] = {}
            recommendation_breakdown = {
                "hire": 0,
                "no_hire": 0,
                "maybe": 0,
                "needs_review": 0
            }
            
            total_score_sum = 0
            score_count = 0
            
            for assessment in all_assessments:
                org_id = str(assessment.get("organization_id", "unknown"))
                
                if org_id not in org_stats_map:
                    org_stats_map[org_id] = OrganizationStats(
                        organization_id=org_id,
                        total_interviews=0,
                        completed_interviews=0,
                        assessed_count=0,
                        pending_assessment=0,
                        average_score=None,
                        hire_count=0,
                        no_hire_count=0
                    )
                
                org_stats = org_stats_map[org_id]
                org_stats.assessed_count += 1
                
                # Track recommendations
                rec = assessment.get("recommendation", "").lower()
                if "hire" in rec and "no" not in rec:
                    recommendation_breakdown["hire"] += 1
                    org_stats.hire_count += 1
                elif "no" in rec or "reject" in rec:
                    recommendation_breakdown["no_hire"] += 1
                    org_stats.no_hire_count += 1
                elif "maybe" in rec or "consider" in rec:
                    recommendation_breakdown["maybe"] += 1
                else:
                    recommendation_breakdown["needs_review"] += 1
                
                # Track scores
                overall_score = assessment.get("overall_score")
                if overall_score is not None:
                    total_score_sum += overall_score
                    score_count += 1
            
            # Calculate averages
            avg_overall = round(total_score_sum / score_count, 2) if score_count > 0 else None
            
            # Get unique organization count
            unique_orgs = len(org_stats_map)
            
            platform_stats = PlatformStats(
                total_organizations=unique_orgs,
                total_interviews=total_assessments,  # Approximation
                total_assessments=total_assessments,
                completed_interviews=total_assessments,
                pending_assessments=0,
                average_overall_score=avg_overall,
                recommendation_breakdown=recommendation_breakdown
            )
            
            return AdminStatsResponse(
                platform=platform_stats,
                organizations=list(org_stats_map.values())
            )
            
    except Exception as e:
        logger.error("admin_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get admin stats: {str(e)}")


@router.get("/assessments", response_model=AdminAssessmentListResponse)
async def get_all_assessments(
    current_user: TokenData = Depends(require_admin),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    recommendation: Optional[str] = Query(None, description="Filter by recommendation (hire/no_hire/maybe)"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum overall score"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum overall score"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort by: overall_score, created_at, recommendation"),
    sort_order: str = Query("desc", description="Sort order: asc, desc")
):
    """
    Get all assessments across organizations with filters.
    
    **Admin Only** - Returns paginated list of all assessments with filtering options.
    """
    try:
        with UnitOfWork() as uow:
            repo = AssessmentRepository(uow.session)
            
            # Get all assessments
            all_assessments = repo.get_all_assessments()
            
            # Apply filters
            filtered = all_assessments
            
            if organization_id:
                filtered = [a for a in filtered if str(a.get("organization_id")) == organization_id]
            
            if recommendation:
                rec_lower = recommendation.lower()
                filtered = [a for a in filtered if rec_lower in a.get("recommendation", "").lower()]
            
            if min_score is not None:
                filtered = [a for a in filtered if (a.get("overall_score") or 0) >= min_score]
            
            if max_score is not None:
                filtered = [a for a in filtered if (a.get("overall_score") or 100) <= max_score]
            
            # Sort
            reverse = sort_order.lower() == "desc"
            if sort_by == "overall_score":
                filtered.sort(key=lambda x: x.get("overall_score") or 0, reverse=reverse)
            elif sort_by == "recommendation":
                filtered.sort(key=lambda x: x.get("recommendation") or "", reverse=reverse)
            else:  # created_at
                filtered.sort(key=lambda x: x.get("created_at") or "", reverse=reverse)
            
            # Paginate
            total_count = len(filtered)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated = filtered[start_idx:end_idx]
            
            # Convert to response model
            assessment_items = [
                AssessmentItem(
                    id=str(a.get("id", "")),
                    interview_id=str(a.get("interview_id", "")),
                    candidate_id=str(a.get("candidate_id")) if a.get("candidate_id") else None,
                    organization_id=str(a.get("organization_id", "")),
                    overall_score=a.get("overall_score", 0),
                    recommendation=a.get("recommendation", ""),
                    technical_score=a.get("technical_score"),
                    communication_score=a.get("communication_score"),
                    soft_skills_score=a.get("soft_skills_score"),
                    proctoring_risk_score=a.get("proctoring_risk_score"),
                    created_at=str(a.get("created_at", ""))
                )
                for a in paginated
            ]
            
            return AdminAssessmentListResponse(
                assessments=assessment_items,
                total_count=total_count,
                page=page,
                page_size=page_size
            )
            
    except Exception as e:
        logger.error("admin_assessments_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get assessments: {str(e)}")


@router.get("/organizations/stats")
async def get_organization_stats(
    current_user: TokenData = Depends(require_admin)
):
    """
    Get detailed statistics for all organizations.
    
    **Admin Only** - Returns per-organization breakdown of assessments and scores.
    """
    try:
        with UnitOfWork() as uow:
            repo = AssessmentRepository(uow.session)
            
            # Get all assessments
            all_assessments = repo.get_all_assessments()
            
            # Group by organization
            org_data: Dict[str, dict] = {}
            
            for assessment in all_assessments:
                org_id = str(assessment.get("organization_id", "unknown"))
                
                if org_id not in org_data:
                    org_data[org_id] = {
                        "organization_id": org_id,
                        "total_assessments": 0,
                        "scores": [],
                        "recommendations": {"hire": 0, "no_hire": 0, "maybe": 0, "other": 0}
                    }
                
                org = org_data[org_id]
                org["total_assessments"] += 1
                
                if assessment.get("overall_score") is not None:
                    org["scores"].append(assessment["overall_score"])
                
                rec = assessment.get("recommendation", "").lower()
                if "hire" in rec and "no" not in rec:
                    org["recommendations"]["hire"] += 1
                elif "no" in rec:
                    org["recommendations"]["no_hire"] += 1
                elif "maybe" in rec:
                    org["recommendations"]["maybe"] += 1
                else:
                    org["recommendations"]["other"] += 1
            
            # Calculate averages
            result = []
            for org_id, data in org_data.items():
                avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else None
                result.append({
                    "organization_id": org_id,
                    "total_assessments": data["total_assessments"],
                    "average_score": round(avg_score, 2) if avg_score else None,
                    "recommendations": data["recommendations"]
                })
            
            return {
                "success": True,
                "data": {
                    "organizations": result,
                    "total_organizations": len(result)
                }
            }
            
    except Exception as e:
        logger.error("org_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get organization stats: {str(e)}")
