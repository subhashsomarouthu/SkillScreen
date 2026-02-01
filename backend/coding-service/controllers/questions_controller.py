"""
Coding Questions Controller - CRUD endpoints for managing coding problems
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
from config.auth import get_current_user, get_current_user_or_candidate, require_role, TokenData, CandidateTokenData


router = APIRouter(prefix="/v1/questions", tags=["Coding Questions"])
log = init_logger("coding-questions")


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class TestCaseInput(BaseModel):
    """Single test case for a coding question"""
    input: str = Field(..., description="Input for the test case")
    expected_output: str = Field(..., alias="expectedOutput", description="Expected output")
    weight: float = Field(default=1.0, ge=0, description="Weight for scoring")
    is_hidden: bool = Field(default=False, alias="isHidden", description="Hidden from candidate")

    class Config:
        populate_by_name = True


class CreateQuestionRequest(BaseModel):
    """Request to create a coding question"""
    title: str = Field(..., min_length=3, max_length=255, description="Question title")
    description: str = Field(..., min_length=10, description="Problem description")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    languages: List[str] = Field(default=["python", "javascript"], description="Supported languages")
    starter_code: Optional[Dict[str, str]] = Field(None, alias="starterCode", description="Starter code per language")
    solution: Optional[Dict[str, str]] = Field(None, description="Solution code per language (hidden)")
    test_cases: List[TestCaseInput] = Field(..., alias="testCases", min_length=1, description="Test cases")
    tags: Optional[List[str]] = Field(None, description="Tags: recursion, arrays, etc.")

    class Config:
        populate_by_name = True


class UpdateQuestionRequest(BaseModel):
    """Request to update a coding question"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    difficulty: Optional[str] = None
    languages: Optional[List[str]] = None
    starter_code: Optional[Dict[str, str]] = Field(None, alias="starterCode")
    solution: Optional[Dict[str, str]] = None
    test_cases: Optional[List[TestCaseInput]] = Field(None, alias="testCases")
    tags: Optional[List[str]] = None

    class Config:
        populate_by_name = True


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("", status_code=201)
async def create_question(
    request: CreateQuestionRequest,
    current_user: TokenData = Depends(require_role("admin", "recruiter", "hiring_manager", "hr", "team_lead"))
):
    """
    Create a new coding question.

    **Authentication Required:** Bearer token with recruiter/hiring_manager/hr/team_lead role.

    **Example:**
    ```json
    {
      "title": "Two Sum",
      "description": "Given an array of integers nums and an integer target...",
      "difficulty": "easy",
      "languages": ["python", "javascript"],
      "testCases": [
        {"input": "2 7 11 15\\n9", "expectedOutput": "0 1", "weight": 1.0},
        {"input": "3 2 4\\n6", "expectedOutput": "1 2", "weight": 1.0, "isHidden": true}
      ],
      "tags": ["arrays", "hash-map"]
    }
    ```
    """
    try:
        if request.difficulty not in ["easy", "medium", "hard"]:
            raise HTTPException(400, "Difficulty must be: easy, medium, or hard")

        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            test_cases = [
                {
                    "input": tc.input,
                    "expectedOutput": tc.expected_output,
                    "weight": tc.weight,
                    "isHidden": tc.is_hidden
                }
                for tc in request.test_cases
            ]

            question = repo.create_question(
                organization_id=current_user.organization_id,
                title=request.title,
                description=request.description,
                difficulty=request.difficulty,
                languages=request.languages,
                starter_code=request.starter_code,
                solution=request.solution,
                test_cases=test_cases,
                tags=request.tags,
                created_by=current_user.user_id
            )

            log.info("question_created", extra={
                "question_id": question["id"],
                "title": request.title,
                "difficulty": request.difficulty
            })

            return create_response(question)

    except HTTPException:
        raise
    except Exception as e:
        log.error("create_question_error", exc_info=e)
        raise HTTPException(500, f"Failed to create question: {str(e)}")


@router.get("")
async def list_questions(
    current_user: TokenData = Depends(require_role("admin", "recruiter", "hiring_manager", "hr", "team_lead")),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: easy, medium, hard"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="Items per page")
):
    """
    List coding questions for the organization.
    Admin users can see all questions across all organizations.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            # Admin can see all questions, others see their org only
            org_id = None if current_user.role == "admin" else current_user.organization_id
            
            result = repo.get_questions_by_organization(
                organization_id=org_id,
                difficulty=difficulty,
                page=page,
                page_size=page_size
            )

            return create_response(result)

    except Exception as e:
        log.error("list_questions_error", exc_info=e)
        raise HTTPException(500, f"Failed to list questions: {str(e)}")


@router.get("/random")
async def get_random_questions(
    current_user: TokenData = Depends(require_role("admin", "recruiter", "hiring_manager", "hr", "team_lead")),
    count: int = Query(1, ge=1, le=10, description="Number of questions"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    exclude: Optional[str] = Query(None, description="Comma-separated question IDs to exclude")
):
    """
    Get random coding questions for an interview.
    """
    try:
        exclude_ids = exclude.split(",") if exclude else None

        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            questions = repo.get_random_questions(
                organization_id=current_user.organization_id,
                count=count,
                difficulty=difficulty,
                exclude_ids=exclude_ids
            )

            return create_response({
                "questions": questions,
                "count": len(questions)
            })

    except Exception as e:
        log.error("get_random_questions_error", exc_info=e)
        raise HTTPException(500, f"Failed to get random questions: {str(e)}")


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    current_user: TokenData = Depends(require_role("admin", "recruiter", "hiring_manager", "hr", "team_lead")),
    include_solution: bool = Query(False, alias="includeSolution", description="Include solution")
):
    """
    Get a specific coding question by ID.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            question = repo.get_question(question_id, include_solution=include_solution)

            if not question:
                raise HTTPException(404, "Question not found")

            # Allow access to own org questions AND platform questions
            platform_org = "00000000-0000-0000-0000-000000000000"
            if question["organization_id"] != current_user.organization_id and question["organization_id"] != platform_org:
                raise HTTPException(403, "Access denied to this question")

            return create_response(question)

    except HTTPException:
        raise
    except Exception as e:
        log.error("get_question_error", exc_info=e)
        raise HTTPException(500, f"Failed to get question: {str(e)}")


@router.put("/{question_id}")
async def update_question(
    question_id: str,
    request: UpdateQuestionRequest,
    current_user: TokenData = Depends(require_role("admin", "recruiter", "hiring_manager", "hr"))
):
    """
    Update a coding question.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            existing = repo.get_question(question_id)
            if not existing:
                raise HTTPException(404, "Question not found")

            platform_org = "00000000-0000-0000-0000-000000000000"
            if existing["organization_id"] == platform_org:
                raise HTTPException(403, "Cannot modify platform questions")
            if existing["organization_id"] != current_user.organization_id:
                raise HTTPException(403, "Access denied to this question")

            updates = {}
            if request.title is not None:
                updates["title"] = request.title
            if request.description is not None:
                updates["description"] = request.description
            if request.difficulty is not None:
                if request.difficulty not in ["easy", "medium", "hard"]:
                    raise HTTPException(400, "Difficulty must be: easy, medium, or hard")
                updates["difficulty"] = request.difficulty
            if request.languages is not None:
                updates["languages"] = request.languages
            if request.starter_code is not None:
                updates["starter_code"] = request.starter_code
            if request.solution is not None:
                updates["solution"] = request.solution
            if request.test_cases is not None:
                updates["test_cases"] = [
                    {
                        "input": tc.input,
                        "expectedOutput": tc.expected_output,
                        "weight": tc.weight,
                        "isHidden": tc.is_hidden
                    }
                    for tc in request.test_cases
                ]
            if request.tags is not None:
                updates["tags"] = request.tags

            if not updates:
                raise HTTPException(400, "No updates provided")

            question = repo.update_question(question_id, **updates)

            log.info("question_updated", extra={"question_id": question_id})

            return create_response(question)

    except HTTPException:
        raise
    except Exception as e:
        log.error("update_question_error", exc_info=e)
        raise HTTPException(500, f"Failed to update question: {str(e)}")


@router.delete("/{question_id}")
async def delete_question(
    question_id: str,
    current_user: TokenData = Depends(require_role("admin", "recruiter", "hiring_manager", "hr"))
):
    """
    Delete (soft delete) a coding question.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            existing = repo.get_question(question_id)
            if not existing:
                raise HTTPException(404, "Question not found")

            platform_org = "00000000-0000-0000-0000-000000000000"
            if existing["organization_id"] == platform_org:
                raise HTTPException(403, "Cannot delete platform questions")
            if existing["organization_id"] != current_user.organization_id:
                raise HTTPException(403, "Access denied to this question")

            repo.delete_question(question_id)

            log.info("question_deleted", extra={"question_id": question_id})

            return create_response({"message": "Question deleted successfully"})

    except HTTPException:
        raise
    except Exception as e:
        log.error("delete_question_error", exc_info=e)
        raise HTTPException(500, f"Failed to delete question: {str(e)}")


# ==========================================
# CANDIDATE ENDPOINT (for interview)
# ==========================================

@router.get("/interview/{question_id}")
async def get_question_for_candidate(
    question_id: str,
    current_user: TokenData | CandidateTokenData = Depends(get_current_user_or_candidate)
):
    """
    Get a coding question for a candidate during interview.
    Accepts both recruiter JWT tokens and candidate interview tokens.
    Does NOT include solution or hidden test cases.
    """
    try:
        with UnitOfWork() as uow:
            repo = CodingRepository(uow)

            question = repo.get_question(question_id, include_solution=False)

            if not question:
                raise HTTPException(404, "Question not found")

            # Filter test cases - hide hidden ones
            visible_test_cases = []
            if question.get("test_cases"):
                for i, tc in enumerate(question["test_cases"]):
                    if not tc.get("isHidden"):
                        visible_test_cases.append({
                            "id": f"tc_{i}",
                            "input": tc.get("input"),
                            "expectedOutput": tc.get("expectedOutput")
                        })

            candidate_question = {
                "id": question["id"],
                "title": question["title"],
                "description": question["description"],
                "difficulty": question["difficulty"],
                "languages": question.get("languages", ["python", "javascript"]),
                "starter_code": question.get("starter_code"),
                "visible_test_cases": visible_test_cases,
                "total_test_cases": len(question.get("test_cases", []))
            }

            return create_response(candidate_question)

    except HTTPException:
        raise
    except Exception as e:
        log.error("get_question_for_candidate_error", exc_info=e)
        raise HTTPException(500, f"Failed to get question: {str(e)}")
