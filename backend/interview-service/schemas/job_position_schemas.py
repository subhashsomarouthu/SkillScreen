from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class InterviewSettingsSchema(BaseModel):
    """Schema for interview settings configuration"""
    # Coding round settings
    has_coding_round: Optional[bool] = Field(False, description="Whether this position has a coding round")
    coding_question_ids: Optional[List[str]] = Field(None, description="List of coding question IDs to assign")
    coding_time_limit: Optional[int] = Field(3600, description="Time limit for coding round in seconds")
    allowed_languages: Optional[List[str]] = Field(None, description="Allowed programming languages")

    # Q&A settings
    qa_question_count: Optional[int] = Field(5, description="Number of Q&A questions")
    qa_time_per_question: Optional[int] = Field(120, description="Time per Q&A question in seconds")

    # General settings
    total_time_limit: Optional[int] = Field(None, description="Total interview time limit in seconds")

    class Config:
        extra = "allow"  # Allow additional fields


class JobPositionCreate(BaseModel):
    """Schema for creating a new job position"""
    organization_id: str = Field(..., description="Organization ID")
    title: str = Field(..., min_length=1, max_length=255, description="Job title")
    description: Optional[str] = Field(None, description="Job description")
    required_skills: Optional[List[str]] = Field(None, description="List of required skills")
    department: Optional[str] = Field(None, max_length=255, description="Department name")
    interview_settings: Optional[InterviewSettingsSchema] = Field(None, description="Interview configuration including coding round")
    is_active: Optional[bool] = Field(True, description="Whether the position is active")
    created_by: Optional[str] = Field(None, description="User ID who created the position")


class JobPositionUpdate(BaseModel):
    """Schema for updating a job position"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Job title")
    description: Optional[str] = Field(None, description="Job description")
    required_skills: Optional[List[str]] = Field(None, description="List of required skills")
    department: Optional[str] = Field(None, max_length=255, description="Department name")
    interview_settings: Optional[InterviewSettingsSchema] = Field(None, description="Interview configuration including coding round")
    is_active: Optional[bool] = Field(None, description="Whether the position is active")


class InterviewSettingsUpdate(BaseModel):
    """Schema for updating only interview settings"""
    has_coding_round: Optional[bool] = Field(None, description="Whether this position has a coding round")
    coding_question_ids: Optional[List[str]] = Field(None, description="List of coding question IDs to assign")
    coding_time_limit: Optional[int] = Field(None, description="Time limit for coding round in seconds")
    allowed_languages: Optional[List[str]] = Field(None, description="Allowed programming languages")
    qa_question_count: Optional[int] = Field(None, description="Number of Q&A questions")
    qa_time_per_question: Optional[int] = Field(None, description="Time per Q&A question in seconds")
    total_time_limit: Optional[int] = Field(None, description="Total interview time limit in seconds")

    class Config:
        extra = "allow"  # Allow additional fields


class JobPositionResponse(BaseModel):
    """Schema for job position response"""
    id: str
    organization_id: str
    title: str
    description: Optional[str]
    required_skills: Optional[List[str]]
    department: Optional[str]
    interview_settings: Optional[Dict[str, Any]]
    is_active: bool
    created_by: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]


class JobPositionListResponse(BaseModel):
    """Schema for list of job positions"""
    job_positions: List[JobPositionResponse]
    total: int
    limit: int
    offset: int


class APIResponse(BaseModel):
    """Standard API response structure"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
