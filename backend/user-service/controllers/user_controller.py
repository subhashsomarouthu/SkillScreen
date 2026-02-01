from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime
from jose import jwt, JWTError
from enum import Enum
import os

from repositories.user_repository import UserRepository
from db import UnitOfWork
from utils.response import create_response
from utilities.logger import init_logger

router = APIRouter()
log = init_logger("user-service")

# JWT Configuration (must match SSO service)
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
security = HTTPBearer()


# ======================
# Request/Response Models
# ======================

class UserRole(str, Enum):
    """Allowed roles for signup (excludes candidate)"""
    recruiter = "recruiter"
    hiring_manager = "hiring_manager"
    team_lead = "team_lead"
    hr = "hr"


class SignupRequest(BaseModel):
    """Full signup - creates organization + user + interview template"""
    # Organization
    company_name: str
    company_domain: Optional[str] = None

    # User
    email: str
    password: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.recruiter  # Default to recruiter

    # Interview template fields (optional - for recruiters)
    interview_type: Optional[str] = None  # behavioral, technical, coding, system_design
    job_role_name: Optional[str] = None   # becomes template name
    questions: Optional[List[Any]] = None  # optional list of questions


class JobPositionCreate(BaseModel):
    """Create job position request"""
    title: str
    description: Optional[str] = None
    required_skills: Optional[List[str]] = []
    department: Optional[str] = None


class JobPositionUpdate(BaseModel):
    """Update job position request"""
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class TokenData(BaseModel):
    user_id: str
    email: str
    organization_id: str
    role: str


# ======================
# Auth Dependency
# ======================

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


# ======================
# Health Endpoints
# ======================

@router.get("/")
def health_check():
    return create_response({
        "message": "User Service is running",
        "status": "deployed",
        "service": "user-service"
    })


@router.get("/health")
def health():
    return create_response({
        "service": "user-service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })


# ======================
# Signup Endpoint (Public)
# ======================

@router.post("/signup")
def signup(req: SignupRequest):
    """
    Register a new recruiter with their company.

    Creates:
    1. New organization
    2. New recruiter user linked to that organization

    This is the main entry point for new recruiters.
    """
    try:
        with UnitOfWork() as uow:
            repo = UserRepository(uow)

            # Check if email already exists
            if repo.email_exists(req.email):
                raise HTTPException(status_code=400, detail="Email already registered")

            # Check if company domain already exists (optional)
            if req.company_domain:
                existing_org = repo.get_organization_by_domain(req.company_domain)
                if existing_org:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Company domain '{req.company_domain}' already registered. Contact your admin."
                    )

            # Create organization
            org = repo.create_organization(
                name=req.company_name,
                domain=req.company_domain
            )

            # Create user with selected role
            user = repo.create_user(
                organization_id=org["id"],
                email=req.email,
                password=req.password,
                first_name=req.first_name,
                last_name=req.last_name,
                role=req.role.value
            )

            # Create interview template if recruiter provides interview type or job role
            template = None
            if req.role == UserRole.recruiter and (req.interview_type or req.job_role_name):
                template_name = req.job_role_name or f"{req.interview_type or 'General'} Interview"
                template = repo.create_interview_template(
                    organization_id=org["id"],
                    name=template_name,
                    template_type=req.interview_type,
                    questions=req.questions,
                    settings={"created_during_signup": True},
                    created_by=user["id"]
                )

            log.info("user_signup_success", extra={
                "user_id": user["id"],
                "organization_id": org["id"],
                "email": req.email,
                "template_created": template is not None
            })

            response_data = {
                "message": "Registration successful! Please login.",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "role": user["role"]
                },
                "organization": {
                    "id": org["id"],
                    "name": org["name"],
                    "domain": org["domain"]
                }
            }

            if template:
                response_data["interview_template"] = template

            return create_response(response_data)

    except HTTPException:
        raise
    except Exception as e:
        log.error("user_signup_error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


# ======================
# User Endpoints
# ======================

@router.get("/users")
def get_users():
    """Get all users (admin only - for debugging)"""
    with UnitOfWork() as uow:
        repo = UserRepository(uow)
        users = repo.get_all_users()
        # Remove password hash from response
        for user in users:
            user.pop("password_hash", None)
        return create_response({"users": users})


@router.get("/users/{user_id}")
def get_user(user_id: str):
    """Get user by ID"""
    with UnitOfWork() as uow:
        repo = UserRepository(uow)
        user = repo.get_user_by_id(user_id)
        if user:
            user.pop("password_hash", None)
            return create_response({"user": user})
        else:
            raise HTTPException(status_code=404, detail="User not found")


@router.get("/me")
def get_current_user_profile(current_user: TokenData = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    with UnitOfWork() as uow:
        repo = UserRepository(uow)
        user = repo.get_user_by_id(current_user.user_id)
        if user:
            user.pop("password_hash", None)
            
            # Fetch organization details (for flags like has_coding_access)
            organization = repo.get_organization_by_id(user["organization_id"])
            
            return create_response({
                "user": user,
                "organization": organization
            })
        else:
            raise HTTPException(status_code=404, detail="User not found")


# ======================
# Job Position Endpoints (Authenticated)
# ======================

@router.post("/job-positions")
def create_job_position(
    req: JobPositionCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new job position for the recruiter's organization.

    Requires authentication.
    """
    try:
        with UnitOfWork() as uow:
            repo = UserRepository(uow)

            job = repo.create_job_position(
                organization_id=current_user.organization_id,
                title=req.title,
                description=req.description,
                required_skills=req.required_skills,
                department=req.department,
                created_by=current_user.user_id
            )

            log.info("job_position_created", extra={
                "job_id": job["id"],
                "organization_id": current_user.organization_id,
                "title": req.title
            })

            return create_response({
                "message": "Job position created successfully",
                "job_position": job
            })

    except Exception as e:
        log.error("job_position_create_error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to create job position: {str(e)}")


@router.get("/job-positions")
def get_job_positions(
    active_only: bool = True,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all job positions for the recruiter's organization.

    Requires authentication.
    """
    try:
        with UnitOfWork() as uow:
            repo = UserRepository(uow)
            jobs = repo.get_job_positions_by_org(
                organization_id=current_user.organization_id,
                active_only=active_only
            )
            return create_response({"job_positions": jobs})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job positions: {str(e)}")


@router.get("/job-positions/{job_id}")
def get_job_position(
    job_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific job position by ID"""
    try:
        with UnitOfWork() as uow:
            repo = UserRepository(uow)
            job = repo.get_job_position_by_id(job_id)

            if not job:
                raise HTTPException(status_code=404, detail="Job position not found")

            # Verify organization ownership
            if job["organization_id"] != current_user.organization_id:
                raise HTTPException(status_code=403, detail="Access denied")

            return create_response({"job_position": job})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job position: {str(e)}")


@router.put("/job-positions/{job_id}")
def update_job_position(
    job_id: str,
    req: JobPositionUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update a job position"""
    try:
        with UnitOfWork() as uow:
            repo = UserRepository(uow)

            # Get existing job
            job = repo.get_job_position_by_id(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job position not found")

            # Verify organization ownership
            if job["organization_id"] != current_user.organization_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Build update dict (only non-None values)
            update_data = {k: v for k, v in req.dict().items() if v is not None}

            if update_data:
                job = repo.update_job_position(job_id, **update_data)

            return create_response({
                "message": "Job position updated successfully",
                "job_position": job
            })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update job position: {str(e)}")


@router.delete("/job-positions/{job_id}")
def delete_job_position(
    job_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete (deactivate) a job position"""
    try:
        with UnitOfWork() as uow:
            repo = UserRepository(uow)

            # Get existing job
            job = repo.get_job_position_by_id(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job position not found")

            # Verify organization ownership
            if job["organization_id"] != current_user.organization_id:
                raise HTTPException(status_code=403, detail="Access denied")

            repo.delete_job_position(job_id)

            return create_response({"message": "Job position deleted successfully"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete job position: {str(e)}")
