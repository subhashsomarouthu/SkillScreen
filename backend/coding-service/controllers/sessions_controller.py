"""
Coding Sessions Controller - Manage candidate code submissions during interviews
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import sys

sys.path.append("/common-service")
from db import UnitOfWork
from utilities.logger import init_logger

from utils.response import create_response
from repositories.coding_repository import CodingRepository
from services.code_execution_service import CodeExecutionService
from config.auth import get_current_user, require_role, TokenData


router = APIRouter(prefix="/v1/sessions", tags=["Coding Sessions"])
log = init_logger("coding-sessions")

# Initialize code execution service
executor_service = CodeExecutionService()

# Judge0 language IDs
LANGUAGE_IDS = {
    "python": 71,      # Python 3
    "javascript": 63,  # JavaScript (Node.js)
    "java": 62,        # Java
    "cpp": 54,         # C++
    "c": 50,           # C
    "go": 60,          # Go
    "rust": 73,        # Rust
    "typescript": 74,  # TypeScript
}


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class StartSessionRequest(BaseModel):
    """Request to start a coding session"""
    interview_id: str = Field(..., alias="interviewId", description="Interview UUID")
    question_id: str = Field(..., alias="questionId", description="Coding question UUID")
    language: str = Field(default="python", description="Programming language")

    class Config:
        populate_by_name = True


class SaveCodeRequest(BaseModel):
    """Request to save code progress"""
    code: str = Field(..., description="Current code")

    class Config:
        populate_by_name = True


class RunCodeRequest(BaseModel):
    """Request to run code"""
    code: str = Field(..., description="Code to run")
    language: str = Field(default="python", description="Programming language")
    stdin: str = Field(default="", description="Custom input")

    class Config:
        populate_by_name = True


class SubmitCodeRequest(BaseModel):
    """Request to submit code for evaluation"""
    code: str = Field(..., description="Final code submission")
    language: str = Field(default="python", description="Programming language")

    class Config:
        populate_by_name = True


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_language_id(language: str) -> int:
    """Get Judge0 language ID from language name"""
    lang = language.lower()
    if lang in LANGUAGE_IDS:
        return LANGUAGE_IDS[lang]
    raise HTTPException(400, f"Unsupported language: {language}. Supported: {list(LANGUAGE_IDS.keys())}")


def _get_all_test_cases(test_cases: List[Dict]) -> List[Dict]:
    """Get all test cases for evaluation"""
    return [
        {
            "id": f"tc_{i}",
            "input": tc.get("input", ""),
            "expectedOutput": tc.get("expectedOutput", ""),
            "weight": tc.get("weight", 1.0)
        }
        for i, tc in enumerate(test_cases)
    ]


def _get_visible_test_cases(test_cases: List[Dict]) -> List[Dict]:
    """Get only visible test cases"""
    return [
        {
            "id": f"tc_{i}",
            "input": tc.get("input", ""),
            "expectedOutput": tc.get("expectedOutput", ""),
            "weight": tc.get("weight", 1.0)
        }
        for i, tc in enumerate(test_cases)
        if not tc.get("isHidden", False)
    ]


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("", status_code=201)
async def start_session(
    request: StartSessionRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Start a new coding session for an interview.

    **Request:**
    ```json
    {
      "interviewId": "uuid",
      "questionId": "uuid",
      "language": "python"
    }
    ```
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            # Get the question
            question = repo.get_question(request.question_id, include_solution=False)
            if not question:
                raise HTTPException(404, "Coding question not found")

            # Check if session already exists
            existing_sessions = repo.get_sessions_by_interview(request.interview_id)
            active_session = next(
                (s for s in existing_sessions
                 if s["question_id"] == request.question_id and s.get("submitted_at") is None),
                None
            )

            if active_session:
                # Return existing session
                return create_response({
                    "session": active_session,
                    "question": {
                        "id": question["id"],
                        "title": question["title"],
                        "description": question["description"],
                        "difficulty": question["difficulty"],
                        "languages": question.get("languages", ["python"]),
                        "starter_code": question.get("starter_code", {}).get(request.language, "")
                    },
                    "message": "Resumed existing session"
                })

            # Get starter code for language
            starter_code = None
            if question.get("starter_code"):
                starter_code = question["starter_code"].get(request.language, "")

            # Create new session
            session = repo.create_session(
                interview_id=request.interview_id,
                question_id=request.question_id,
                language=request.language,
                starter_code=starter_code
            )

            log.info("coding_session_started", extra={
                "session_id": session["id"],
                "interview_id": request.interview_id,
                "question_id": request.question_id
            })

            # Get visible test cases
            visible_test_cases = _get_visible_test_cases(question.get("test_cases", []))

            return create_response({
                "session": session,
                "question": {
                    "id": question["id"],
                    "title": question["title"],
                    "description": question["description"],
                    "difficulty": question["difficulty"],
                    "languages": question.get("languages", ["python"]),
                    "starter_code": starter_code,
                    "visible_test_cases": visible_test_cases,
                    "total_test_cases": len(question.get("test_cases", []))
                },
                "message": "Session started successfully"
            })

    except HTTPException:
        raise
    except Exception as e:
        log.error("start_session_error", exc_info=e)
        raise HTTPException(500, f"Failed to start session: {str(e)}")


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get a coding session by ID.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            session = repo.get_session(session_id)
            if not session:
                raise HTTPException(404, "Session not found")

            return create_response({"session": session})

    except HTTPException:
        raise
    except Exception as e:
        log.error("get_session_error", exc_info=e)
        raise HTTPException(500, f"Failed to get session: {str(e)}")


@router.put("/{session_id}/save")
async def save_code(
    session_id: str,
    request: SaveCodeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Auto-save code progress.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            session = repo.get_session(session_id)
            if not session:
                raise HTTPException(404, "Session not found")

            if session.get("submitted_at"):
                raise HTTPException(400, "Cannot save code: session already submitted")

            repo.update_session_code(session_id, request.code)

            return create_response({
                "message": "Code saved",
                "session_id": session_id
            })

    except HTTPException:
        raise
    except Exception as e:
        log.error("save_code_error", exc_info=e)
        raise HTTPException(500, f"Failed to save code: {str(e)}")


@router.post("/{session_id}/run")
async def run_code(
    session_id: str,
    request: RunCodeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Run code with custom input (for testing).
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            session = repo.get_session(session_id)
            if not session:
                raise HTTPException(404, "Session not found")

        # Get language ID
        language_id = get_language_id(request.language)

        # Execute code via Judge0
        result = await executor_service.run_code(
            language_id=language_id,
            source_code=request.code,
            stdin=request.stdin
        )

        log.info("code_run", extra={
            "session_id": session_id,
            "status": result["status"]
        })

        return create_response({
            "execution": result,
            "session_id": session_id
        })

    except HTTPException:
        raise
    except Exception as e:
        log.error("run_code_error", exc_info=e)
        raise HTTPException(500, f"Failed to run code: {str(e)}")


@router.post("/{session_id}/test")
async def test_against_visible(
    session_id: str,
    request: RunCodeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Test code against visible test cases only.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            session = repo.get_session(session_id)
            if not session:
                raise HTTPException(404, "Session not found")

            # Get question and visible test cases
            question = repo.get_question(session["question_id"], include_solution=False)
            if not question:
                raise HTTPException(404, "Question not found")

            visible_test_cases = _get_visible_test_cases(question.get("test_cases", []))

            if not visible_test_cases:
                raise HTTPException(400, "No visible test cases available")

        # Get language ID
        language_id = get_language_id(request.language)

        # Run against visible test cases
        result = await executor_service.evaluate_code(
            language_id=language_id,
            source_code=request.code,
            test_cases=visible_test_cases
        )

        log.info("code_tested", extra={
            "session_id": session_id,
            "score": result["score"]
        })

        return create_response({
            "test_results": result,
            "session_id": session_id,
            "note": "This tests only visible cases. Final evaluation includes hidden cases."
        })

    except HTTPException:
        raise
    except Exception as e:
        log.error("test_code_error", exc_info=e)
        raise HTTPException(500, f"Failed to test code: {str(e)}")


@router.post("/{session_id}/submit")
async def submit_code(
    session_id: str,
    request: SubmitCodeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Submit code for final evaluation against ALL test cases.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            session = repo.get_session(session_id)
            if not session:
                raise HTTPException(404, "Session not found")

            if session.get("submitted_at"):
                raise HTTPException(400, "Code already submitted")

            # Get question with all test cases
            question = repo.get_question(session["question_id"], include_solution=False)
            if not question:
                raise HTTPException(404, "Question not found")

            all_test_cases = _get_all_test_cases(question.get("test_cases", []))

            if not all_test_cases:
                raise HTTPException(400, "No test cases defined")

        # Get language ID
        language_id = get_language_id(request.language)

        # Run against ALL test cases
        result = await executor_service.evaluate_code(
            language_id=language_id,
            source_code=request.code,
            test_cases=all_test_cases
        )

        # Calculate metrics
        passed_count = sum(1 for r in result["results"] if r["passed"])
        total_count = len(result["results"])
        is_correct = passed_count == total_count
        avg_time = sum(r.get("time", 0) or 0 for r in result["results"]) / total_count if total_count > 0 else 0
        max_memory = max((r.get("memory", 0) or 0 for r in result["results"]), default=0)

        # Save submission
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            repo.submit_session(
                session_id=session_id,
                code=request.code,
                execution_results=result,
                is_correct=is_correct,
                execution_time=int(avg_time * 1000),  # Convert to ms
                memory_usage=max_memory
            )

        log.info("code_submitted", extra={
            "session_id": session_id,
            "is_correct": is_correct,
            "passed": passed_count,
            "total": total_count
        })

        # Prepare response (hide expected outputs for hidden test cases)
        safe_results = []
        for i, r in enumerate(result["results"]):
            test_case = question["test_cases"][i] if i < len(question["test_cases"]) else {}
            is_hidden = test_case.get("isHidden", False)

            safe_result = {
                "testCaseId": r["testCaseId"],
                "passed": r["passed"],
                "status": r["status"],
                "time": r["time"],
                "memory": r["memory"]
            }

            if not is_hidden:
                safe_result["stdout"] = r["stdout"]
                safe_result["stderr"] = r["stderr"]
            else:
                safe_result["hidden"] = True

            safe_results.append(safe_result)

        return create_response({
            "session_id": session_id,
            "is_correct": is_correct,
            "score": result["score"],
            "passed_count": passed_count,
            "total_count": total_count,
            "score_percentage": round(result["score"] * 100, 1),
            "execution_time_ms": round(avg_time * 1000, 2),
            "memory_used_kb": max_memory,
            "results": safe_results
        })

    except HTTPException:
        raise
    except Exception as e:
        log.error("submit_code_error", exc_info=e)
        raise HTTPException(500, f"Failed to submit code: {str(e)}")


# ==========================================
# RECRUITER ENDPOINTS
# ==========================================

@router.get("/interview/{interview_id}")
async def get_interview_sessions(
    interview_id: str,
    current_user: TokenData = Depends(require_role("recruiter", "hiring_manager", "hr", "team_lead"))
):
    """
    Get all coding sessions for an interview.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            sessions = repo.get_sessions_by_interview(interview_id)

            # Enrich with question info
            enriched_sessions = []
            for session in sessions:
                question = repo.get_question(session["question_id"], include_solution=True)
                enriched_sessions.append({
                    **session,
                    "question": question
                })

            return create_response({
                "interview_id": interview_id,
                "sessions": enriched_sessions,
                "count": len(enriched_sessions)
            })

    except Exception as e:
        log.error("get_interview_sessions_error", exc_info=e)
        raise HTTPException(500, f"Failed to get sessions: {str(e)}")


@router.get("/stats")
async def get_coding_stats(
    current_user: TokenData = Depends(require_role("recruiter", "hiring_manager", "hr", "team_lead"))
):
    """
    Get coding session statistics for the organization.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            stats = repo.get_session_stats(current_user.organization_id)

            return create_response(stats)

    except Exception as e:
        log.error("get_coding_stats_error", exc_info=e)
        raise HTTPException(500, f"Failed to get stats: {str(e)}")
