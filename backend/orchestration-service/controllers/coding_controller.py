"""
Coding Controller - Orchestrates coding round during interviews
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from services.service_client import service_client
from services.interview_service_client import InterviewServiceClient
from config.logger import logger

interview_client = InterviewServiceClient()


class AssignQuestionsRequest(BaseModel):
    question_ids: List[str]


class StartCodingSessionRequest(BaseModel):
    interview_id: str
    question_id: str
    language: str = "python"


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


@router.get("/questions/{question_id}")
async def get_question_for_candidate(
    question_id: str,
    authorization: str = Header(None)
):
    """
    Get a specific coding question for a candidate during interview.
    Does NOT include solution or hidden test cases.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Getting coding question {question_id} for candidate")
        result = await service_client.get_coding_question_for_candidate(token, question_id)
        return create_response(
            data=result.get("data", {}),
            message="Coding question retrieved"
        )
    except Exception as e:
        logger.error(f"Failed to get coding question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get question: {str(e)}")


@router.post("/sessions/start")
async def start_coding_stage(
    request: StartCodingSessionRequest,
    authorization: str = Header(None)
):
    """
    Start a coding session for a candidate during an interview.

    Called when the candidate transitions to the coding round.
    Creates a session in the coding-service linked to the interview.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Starting coding session: interview={request.interview_id}, question={request.question_id}")

        result = await service_client.start_coding_session(
            auth_token=token,
            interview_id=request.interview_id,
            question_id=request.question_id,
            language=request.language
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


class RunCodeRequest(BaseModel):
    code: str
    language: str = "python"
    stdin: str = ""


class SubmitCodeRequest(BaseModel):
    code: str
    language: str = "python"


@router.post("/sessions/{session_id}/run")
async def run_code(
    session_id: str,
    request: RunCodeRequest,
    authorization: str = Header(None)
):
    """
    Run code with custom input for testing.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Running code for session {session_id}")
        result = await service_client.run_code(
            auth_token=token,
            session_id=session_id,
            code=request.code,
            language=request.language,
            stdin=request.stdin
        )
        return create_response(
            data=result.get("data", {}),
            message="Code executed"
        )
    except Exception as e:
        logger.error(f"Failed to run code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to run code: {str(e)}")


@router.post("/sessions/{session_id}/test")
async def test_code(
    session_id: str,
    request: RunCodeRequest,
    authorization: str = Header(None)
):
    """
    Test code against visible test cases.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Testing code for session {session_id}")
        result = await service_client.test_code(
            auth_token=token,
            session_id=session_id,
            code=request.code,
            language=request.language
        )
        return create_response(
            data=result.get("data", {}),
            message="Code tested"
        )
    except Exception as e:
        logger.error(f"Failed to test code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test code: {str(e)}")


@router.post("/sessions/{session_id}/submit")
async def submit_code(
    session_id: str,
    request: SubmitCodeRequest,
    authorization: str = Header(None)
):
    """
    Submit code for final evaluation against ALL test cases.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Submitting code for session {session_id}")
        result = await service_client.submit_code(
            auth_token=token,
            session_id=session_id,
            code=request.code,
            language=request.language
        )
        return create_response(
            data=result.get("data", {}),
            message="Code submitted"
        )
    except Exception as e:
        logger.error(f"Failed to submit code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit code: {str(e)}")


@router.post("/interviews/{interview_id}/assign-questions")
async def assign_coding_questions(
    interview_id: str,
    request: AssignQuestionsRequest,
    authorization: str = Header(None)
):
    """
    Assign coding questions to an interview.
    Called by recruiter when setting up the interview.
    Stores question IDs in interview settings JSONB.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Assigning {len(request.question_ids)} coding questions to interview {interview_id}")

        # Validate that the questions exist
        questions_result = await service_client.get_coding_questions(token)
        available_ids = [q["id"] for q in questions_result.get("data", {}).get("questions", [])]

        invalid_ids = [qid for qid in request.question_ids if qid not in available_ids]
        if invalid_ids:
            raise HTTPException(status_code=400, detail=f"Invalid question IDs: {invalid_ids}")

        # Update interview settings with coding question IDs
        settings_update = {
            "coding_question_ids": request.question_ids,
            "has_coding_round": True
        }

        result = await interview_client.update_interview_settings(interview_id, settings_update)

        logger.info(f"Coding questions assigned to interview {interview_id}")

        return create_response(
            data={
                "interview_id": interview_id,
                "coding_question_ids": request.question_ids,
                "questions_assigned": len(request.question_ids)
            },
            message="Coding questions assigned to interview"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign coding questions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to assign questions: {str(e)}")


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


@router.post("/interviews/{interview_id}/complete")
async def complete_coding_round(
    interview_id: str,
    authorization: str = Header(None)
):
    """
    Complete the coding round for an interview.

    This endpoint:
    1. Validates all coding sessions are submitted
    2. Saves coding results to ai_analysis table for assessment
    3. Updates interview status to 'completed'

    Should be called when candidate finishes all coding questions.
    After this, the assessment can be generated.
    """
    token = _extract_token(authorization)

    try:
        logger.info(f"Completing coding round for interview {interview_id}")

        # Call coding service to complete the round
        result = await service_client.complete_coding_round(token, interview_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to complete coding round"))

        data = result.get("data", {})

        logger.info(f"Coding round completed for interview {interview_id}: {data.get('coding_summary', {})}")

        return create_response(
            data=data,
            message="Coding round completed. Interview ready for assessment."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete coding round: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete coding round: {str(e)}")
