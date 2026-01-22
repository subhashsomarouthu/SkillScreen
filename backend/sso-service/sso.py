from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Any
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy import Table, Column, String, Boolean, MetaData, select
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import os
import sys

sys.path.append('/common-service')
from db import DBFactory, UnitOfWork

# ======================
# Configuration
# ======================
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "8"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Initialize DB
DBFactory.init()

app = FastAPI(title="SSO Service", version="1.0.0")


# ======================
# Database Tables
# ======================
metadata = MetaData()

users_table = Table(
    "users", metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID, nullable=False),
    Column("email", String, nullable=False),
    Column("password_hash", String),
    Column("first_name", String),
    Column("last_name", String),
    Column("role", String, nullable=False),
    Column("is_active", Boolean, default=True),
    Column("profile_data", JSONB),
)

organizations_table = Table(
    "organizations", metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String, nullable=False),
    Column("domain", String),
)

interview_templates_table = Table(
    "interview_templates", metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID, nullable=False),
    Column("name", String, nullable=False),
    Column("type", String),
    Column("questions", JSONB),
    Column("settings", JSONB),
    Column("created_by", UUID),
)


# ======================
# Helpers
# ======================
def create_response(data, success=True):
    """Create standardized API response"""
    return {
        "success": success,
        "data": data,
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "version": "v1"
        }
    }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ======================
# Request/Response Models
# ======================
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str = "recruiter"
    organization_id: str
    # Interview template fields (optional - for recruiters)
    interview_type: Optional[str] = None  # behavioral, technical, coding, system_design
    job_role_name: Optional[str] = None   # becomes template name
    questions: Optional[List[Any]] = None  # optional list of questions


class TokenData(BaseModel):
    user_id: str
    email: str
    organization_id: str
    role: str


# ======================
# Auth Dependencies
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
# Endpoints
# ======================
@app.get("/")
def health_check():
    """Health check endpoint"""
    return create_response({
        "message": "SSO Service is running",
        "status": "deployed",
        "service": "sso-service"
    })


@app.get("/health")
def health():
    """Detailed health check"""
    return create_response({
        "service": "sso-service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.post("/login")
def login(req: LoginRequest):
    """
    User login endpoint.

    Authenticates user with email/password and returns JWT token
    containing user_id, email, organization_id, and role.
    """
    with UnitOfWork() as uow:
        # Find user by email
        query = select(users_table).where(
            users_table.c.email == req.email,
            users_table.c.is_active == True
        )
        result = uow.session.execute(query).fetchone()

        if not result:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user = dict(result._mapping)

        # Verify password
        if not user.get("password_hash"):
            raise HTTPException(status_code=401, detail="Password not set for this account")

        if not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Create JWT token with organization_id
        token = create_access_token({
            "sub": str(user["id"]),
            "email": user["email"],
            "organization_id": str(user["organization_id"]),
            "role": user["role"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name")
        })

        return create_response({
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "role": user["role"],
                "organization_id": str(user["organization_id"])
            },
            "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600
        })


@app.post("/register")
def register(req: RegisterRequest):
    """
    Register a new user (recruiter/hiring_manager).

    Creates a new user account linked to an organization.
    """
    with UnitOfWork() as uow:
        # Check if email already exists
        existing = uow.session.execute(
            select(users_table).where(users_table.c.email == req.email)
        ).fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Verify organization exists
        org = uow.session.execute(
            select(organizations_table).where(
                organizations_table.c.id == uuid.UUID(req.organization_id)
            )
        ).fetchone()

        if not org:
            raise HTTPException(status_code=400, detail="Organization not found")

        # Create user
        user_id = uuid.uuid4()
        insert_stmt = users_table.insert().values(
            id=user_id,
            organization_id=uuid.UUID(req.organization_id),
            email=req.email,
            password_hash=hash_password(req.password),
            first_name=req.first_name,
            last_name=req.last_name,
            role=req.role,
            is_active=True
        )
        uow.session.execute(insert_stmt)

        # Create interview template if recruiter provides interview type or job role
        template_id = None
        if req.role == "recruiter" and (req.interview_type or req.job_role_name):
            template_id = uuid.uuid4()
            template_name = req.job_role_name or f"{req.interview_type or 'General'} Interview"
            template_insert = interview_templates_table.insert().values(
                id=template_id,
                organization_id=uuid.UUID(req.organization_id),
                name=template_name,
                type=req.interview_type,
                questions=req.questions,
                settings={"created_during_registration": True},
                created_by=user_id
            )
            uow.session.execute(template_insert)

        response_data = {
            "message": "User registered successfully",
            "user_id": str(user_id),
            "email": req.email
        }

        if template_id:
            response_data["interview_template_id"] = str(template_id)
            response_data["template_name"] = template_name

        return create_response(response_data)


@app.get("/me")
def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current authenticated user info"""
    with UnitOfWork() as uow:
        query = select(users_table, organizations_table.c.name.label("organization_name")).select_from(
            users_table.join(organizations_table, users_table.c.organization_id == organizations_table.c.id)
        ).where(users_table.c.id == uuid.UUID(current_user.user_id))

        result = uow.session.execute(query).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        user = dict(result._mapping)

        return create_response({
            "id": str(user["id"]),
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "role": user["role"],
            "organization_id": str(user["organization_id"]),
            "organization_name": user.get("organization_name"),
            "is_active": user["is_active"]
        })


@app.post("/verify")
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify JWT token and return decoded payload.

    Used by other services to validate tokens.
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return create_response({
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "organization_id": payload.get("organization_id"),
            "role": payload.get("role"),
            "exp": payload.get("exp")
        })
    except JWTError as e:
        return create_response({
            "valid": False,
            "error": str(e)
        }, success=False)