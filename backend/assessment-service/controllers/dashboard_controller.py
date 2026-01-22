from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import sys
sys.path.append('/common-service')
from db import UnitOfWork
from repositories.assessment_repository import AssessmentRepository
from config.auth import get_current_user, require_role, TokenData


router = APIRouter(prefix="/v1/dashboard", tags=["Recruiter Dashboard"])


# ==========================================
# RESPONSE MODELS
# ==========================================

class AssessmentSummary(BaseModel):
    """Assessment summary for dashboard"""
    id: Optional[str]
    overall_score: Optional[float]
    recommendation: Optional[str]
    technical_score: Optional[float]
    communication_score: Optional[float]
    soft_skills_score: Optional[float]
    proctoring_risk_score: Optional[float]
    created_at: Optional[str]


class CandidateItem(BaseModel):
    """Single candidate item for dashboard list"""
    interview_id: Optional[str]
    candidate_id: Optional[str]
    candidate_name: str
    candidate_email: Optional[str]
    job_position_id: Optional[str]
    job_title: str
    status: str  # assessed, pending, in_progress, scheduled
    interview_completed_at: Optional[str]
    assessment: Optional[AssessmentSummary]


class PaginationInfo(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool


class DashboardListResponse(BaseModel):
    """Response for dashboard candidate list"""
    candidates: List[CandidateItem]
    pagination: PaginationInfo


class RecommendationStats(BaseModel):
    """Recommendation breakdown"""
    hire: int = 0
    no_hire: int = 0
    maybe: int = 0
    needs_review: int = 0


class AverageScores(BaseModel):
    """Average scores across assessments"""
    overall: Optional[float]
    technical: Optional[float]
    communication: Optional[float]
    soft_skills: Optional[float]


class DashboardStatsResponse(BaseModel):
    """Response for dashboard statistics"""
    total_interviews: int
    completed_interviews: int
    assessed_count: int
    pending_count: int
    in_progress_count: int
    recommendations: RecommendationStats
    average_scores: AverageScores


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/candidates", response_model=DashboardListResponse)
async def get_dashboard_candidates(
    current_user: TokenData = Depends(require_role("recruiter", "hiring_manager", "hr", "team_lead")),
    job_position_id: Optional[str] = Query(None, description="Filter by job position UUID"),
    recommendation: Optional[str] = Query(None, description="Filter by recommendation: hire, no_hire, maybe, needs_review"),
    status: Optional[str] = Query(None, description="Filter by status: assessed, pending, in_progress"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum overall score"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum overall score"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort by: overall_score, created_at, name, recommendation"),
    sort_order: str = Query("desc", description="Sort order: asc, desc")
):
    """
    Get paginated list of candidates for recruiter dashboard.

    **Authentication Required:** Bearer token with recruiter/hiring_manager/hr/team_lead role.
    Organization is automatically filtered based on the authenticated user's organization.

    **Features:**
    - Lists all candidates with their interview and assessment status
    - Supports filtering by job position, recommendation, status, and score range
    - Supports pagination and sorting
    - Shows both assessed candidates (with scores) and pending ones

    **Status Values:**
    - `assessed`: Interview completed and assessment generated
    - `pending`: Interview completed but assessment not yet generated
    - `in_progress`: Interview in progress
    - `scheduled`: Interview scheduled but not started

    **Example:**
    ```
    GET /v1/dashboard/candidates?status=assessed&recommendation=hire&sort_by=overall_score&sort_order=desc
    Authorization: Bearer <token>
    ```
    """
    try:
        with UnitOfWork() as uow:
            repo = AssessmentRepository(uow)

            # Organization ID comes from JWT token (secure multi-tenant filtering)
            result = repo.get_dashboard_candidates(
                organization_id=current_user.organization_id,
                job_position_id=job_position_id,
                recommendation=recommendation,
                status=status,
                min_score=min_score,
                max_score=max_score,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order
            )

            return DashboardListResponse(
                candidates=[CandidateItem(**c) for c in result["candidates"]],
                pagination=PaginationInfo(**result["pagination"])
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard data: {str(e)}")


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: TokenData = Depends(require_role("recruiter", "hiring_manager", "hr", "team_lead")),
    job_position_id: Optional[str] = Query(None, description="Filter by job position UUID")
):
    """
    Get summary statistics for recruiter dashboard.

    **Authentication Required:** Bearer token with recruiter/hiring_manager/hr/team_lead role.
    Organization is automatically filtered based on the authenticated user's organization.

    **Returns:**
    - Total interviews count
    - Completed vs in-progress breakdown
    - Assessed vs pending breakdown
    - Recommendation distribution (hire, no_hire, maybe, needs_review)
    - Average scores across all assessments

    **Example:**
    ```
    GET /v1/dashboard/stats?job_position_id=uuid-here
    Authorization: Bearer <token>
    ```
    """
    try:
        with UnitOfWork() as uow:
            repo = AssessmentRepository(uow)

            # Organization ID comes from JWT token (secure multi-tenant filtering)
            stats = repo.get_dashboard_stats(
                organization_id=current_user.organization_id,
                job_position_id=job_position_id
            )

            return DashboardStatsResponse(
                total_interviews=stats["total_interviews"],
                completed_interviews=stats["completed_interviews"],
                assessed_count=stats["assessed_count"],
                pending_count=stats["pending_count"],
                in_progress_count=stats["in_progress_count"],
                recommendations=RecommendationStats(**stats["recommendations"]),
                average_scores=AverageScores(**stats["average_scores"])
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")


@router.post("/generate-pending")
async def generate_pending_assessments(
    current_user: TokenData = Depends(require_role("recruiter", "hiring_manager", "hr")),
    job_position_id: Optional[str] = Query(None, description="Filter by job position UUID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum assessments to generate")
):
    """
    Trigger assessment generation for pending interviews.

    **Authentication Required:** Bearer token with recruiter/hiring_manager/hr role.
    Only processes interviews from the authenticated user's organization.

    This endpoint allows recruiters to manually trigger assessment generation
    for interviews that are completed but don't have assessments yet.

    **Use Case:**
    - When recruiter wants to see results immediately without waiting for scheduler
    - To process a batch of pending interviews on-demand

    **Returns:**
    - Count of successfully generated assessments
    - List of interview IDs that were processed
    """
    try:
        from services.assessment_service import AssessmentService
        assessment_service = AssessmentService()

        with UnitOfWork() as uow:
            repo = AssessmentRepository(uow)

            # Get pending interviews
            pending = repo.get_completed_interviews_without_assessment(limit=limit)

            # Filter by user's organization (from JWT token - secure multi-tenant)
            pending = [p for p in pending if str(p.get('organization_id')) == current_user.organization_id]

            # Optionally filter by job position
            if job_position_id:
                pending = [p for p in pending if str(p.get('job_position_id')) == job_position_id]

        # Generate assessments
        results = {
            "success": [],
            "failed": [],
            "skipped": []
        }

        for interview in pending[:limit]:
            interview_id = str(interview['id'])
            try:
                result = await assessment_service.generate_assessment(interview_id)

                if result['status'] == 'success':
                    results["success"].append(interview_id)
                elif result['status'] in ['incomplete', 'already_exists']:
                    results["skipped"].append(interview_id)
                else:
                    results["failed"].append(interview_id)

            except Exception as e:
                results["failed"].append(interview_id)

        return {
            "status": "completed",
            "total_processed": len(pending[:limit]),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "skipped_count": len(results["skipped"]),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating assessments: {str(e)}")
