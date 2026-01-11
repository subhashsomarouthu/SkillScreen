"""
Schemas for interview video processing endpoints
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, timezone


class ProcessInterviewVideoRequest(BaseModel):
    """Request schema for interview video processing"""
    interview_id: UUID = Field(..., description="Interview UUID")
    session_id: UUID = Field(..., description="Session UUID (question)")
    media_file_id: UUID = Field(..., description="Media file UUID")

    class Config:
        json_schema_extra = {
            "example": {
                "interview_id": "d37f8d3d-5c68-5f56-8a9d-59d040850c90",
                "session_id": "f211e428-3aab-4c52-abb3-c3f5f0a957c6",
                "media_file_id": "609f1983-1f85-4f33-96a6-fe67d9ba7742"
            }
        }


class ProcessInterviewVideoResponse(BaseModel):
    """Response schema for interview video processing"""
    status: str = Field(..., description="'accepted' - processing started")
    message: str = Field(..., description="Status message")
    media_file_id: str
    interview_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "message": "Video processing started in background",
                "media_file_id": "609f1983-1f85-4f33-96a6-fe67d9ba7742",
                "interview_id": "d37f8d3d-5c68-5f56-8a9d-59d040850c90",
                "session_id": "f211e428-3aab-4c52-abb3-c3f5f0a957c6",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }
