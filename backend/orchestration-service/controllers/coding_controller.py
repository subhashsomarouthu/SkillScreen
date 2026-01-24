"""
Coding Controller - Orchestrates coding round during interviews
"""

from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone
from typing import Optional
import uuid

from services.service_client import service_client
from config.logger import logger


router = APIRouter()


def create_response(data, success=True, message="Success"):
    """Create standardized API response"""
    return {
        "success": success,
        "message": message,
        "data": data,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "v1",
            "request_id": f"req_{uuid.uuid4().hex[:8]}"
        }
    }


def _extract_token(authorization: str) -> str:
    """Extract bearer token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return authorization.replace("Bearer ", "")


# ========================================
# CODING STAGE ENDPOINTS
# ========================================

@router.get("/questions")
async def get_available_questions(
    difficulty: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    Get available coding questions from the question bank.
    Used by recruiters to select questions for interviews.
    """
    token = _extract_token(authorization)

    try:
        result = await service_client.get_coding_questions(token, difficulty)
        return create_response(
            data=result.get("data", {}),
            message="Coding questions retrieved"
        )
    except Exception as e:
        logger.error(f"Failed to get coding questions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")


@router.post("/sessions/start")
async def start_coding_stage(
    interview_id: str,
    question_id: str,
    language: str = "python",
    authorization: str = Header(None)
):
    """
    Start a coding session for a candidate during an interview.

    Called when the candidate transitions to the coding round.
    Creates a session in the coding-service linked to the interview.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Starting coding session: interview={interview_id}, question={question_id}")

        result = await service_client.start_coding_session(
            auth_token=token,
            interview_id=interview_id,
            question_id=question_id,
            language=language
        )

        session_data = result.get("data", {})

        logger.info(f"Coding session started: {session_data.get('session', {}).get('id')}")

        return create_response(
            data=session_data,
            message="Coding session started"
        )
    except Exception as e:
        logger.error(f"Failed to start coding session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start coding session: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_coding_session(
    session_id: str,
    authorization: str = Header(None)
):
    """
    Get a coding session's details and results.
    """
    token = _extract_token(authorization)

    try:
        result = await service_client.get_coding_session(token, session_id)
        return create_response(
            data=result.get("data", {}),
            message="Coding session retrieved"
        )
    except Exception as e:
        logger.error(f"Failed to get coding session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.get("/interviews/{interview_id}/results")
async def get_coding_results(
    interview_id: str,
    authorization: str = Header(None)
):
    """
    Get all coding session results for an interview.
    Used by recruiters to review candidate's coding performance.
    """
    token = _extract_token(authorization)

    try:
        result = await service_client.get_coding_sessions_by_interview(token, interview_id)
        sessions = result.get("data", {}).get("sessions", [])

        # Calculate summary
        total_sessions = len(sessions)
        submitted_sessions = [s for s in sessions if s.get("submitted_at")]
        correct_sessions = [s for s in submitted_sessions if s.get("is_correct")]

        summary = {
            "interview_id": interview_id,
            "total_questions": total_sessions,
            "submitted": len(submitted_sessions),
            "correct": len(correct_sessions),
            "score_percentage": round(len(correct_sessions) / len(submitted_sessions) * 100, 1) if submitted_sessions else 0,
            "sessions": sessions
        }

        return create_response(
            data=summary,
            message="Coding results retrieved"
        )
    except Exception as e:
        logger.error(f"Failed to get coding results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get coding results: {str(e)}")
