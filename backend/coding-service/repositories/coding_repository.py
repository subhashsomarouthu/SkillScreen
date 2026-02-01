import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Table, Column, String, Integer, Float, Boolean, DateTime, Text, MetaData, select, and_, or_, func, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session

# Platform-wide questions are available to all organizations
PLATFORM_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


metadata = MetaData()

# ==========================================
# TABLE DEFINITIONS (matching existing schema)
# ==========================================

# Enum for difficulty
difficulty_enum = Enum('easy', 'medium', 'hard', name='difficulty_level', create_type=False)

coding_questions_table = Table(
    "coding_questions", metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID, nullable=False),
    Column("title", String, nullable=False),
    Column("description", Text),
    Column("difficulty", difficulty_enum),  # easy, medium, hard (enum)
    Column("languages", JSONB),              # supported languages
    Column("test_cases", JSONB),             # [{ input, expectedOutput, weight, isHidden }]
    Column("starter_code", JSONB),           # { "python": "...", "javascript": "..." }
    Column("solution", JSONB),               # { "python": "...", "javascript": "..." }
    Column("tags", JSONB),                   # ["recursion", "binary-search", etc.]
    Column("created_by", UUID),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
    Column("deleted_at", DateTime),
)

coding_sessions_table = Table(
    "coding_sessions", metadata,
    Column("id", UUID, primary_key=True),
    Column("interview_id", UUID, nullable=False),
    Column("question_id", UUID, nullable=False),
    Column("language", String),              # language used (python, javascript, etc.)
    Column("code", Text),                    # submitted code
    Column("execution_results", JSONB),      # results from Judge0
    Column("is_correct", Boolean),           # passed all tests?
    Column("execution_time", Integer),       # ms
    Column("memory_usage", Integer),         # KB
    Column("started_at", DateTime),
    Column("submitted_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
)

ai_analysis_table = Table(
    "ai_analysis", metadata,
    Column("id", UUID, primary_key=True),
    Column("interview_id", UUID),
    Column("session_id", UUID),
    Column("analysis_type", String),
    Column("service_name", String),
    Column("raw_results", JSONB),
    Column("confidence_score", Float),
    Column("processing_time", Integer),
    Column("version", String),
    Column("created_at", DateTime),
)

interviews_table = Table(
    "interviews", metadata,
    Column("id", UUID, primary_key=True),
    Column("status", String),
    Column("completed_at", DateTime),
)


class CodingRepository:
    """Repository for coding questions and sessions database operations"""

    def __init__(self, uow):
        self.session: Session = uow.session

    # ==========================================
    # CODING QUESTIONS METHODS
    # ==========================================

    def create_question(
        self,
        organization_id: str,
        title: str,
        description: str = None,
        difficulty: str = "medium",
        languages: List[str] = None,
        starter_code: Dict[str, str] = None,
        solution: Dict[str, str] = None,
        test_cases: List[Dict] = None,
        tags: List[str] = None,
        created_by: str = None
    ) -> Dict[str, Any]:
        """Create a new coding question"""
        question_id = uuid.uuid4()

        insert_stmt = coding_questions_table.insert().values(
            id=question_id,
            organization_id=uuid.UUID(organization_id),
            title=title,
            description=description,
            difficulty=difficulty,
            languages=languages or ["python", "javascript"],
            starter_code=starter_code or {},
            solution=solution or {},
            test_cases=test_cases or [],
            tags=tags or [],
            created_by=uuid.UUID(created_by) if created_by else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.session.execute(insert_stmt)

        return {
            "id": str(question_id),
            "organization_id": organization_id,
            "title": title,
            "description": description,
            "difficulty": difficulty,
            "languages": languages or ["python", "javascript"],
            "test_cases_count": len(test_cases) if test_cases else 0,
            "tags": tags or []
        }

    def get_question(self, question_id: str, include_solution: bool = False) -> Optional[Dict[str, Any]]:
        """Get a coding question by ID"""
        query = select(coding_questions_table).where(
            and_(
                coding_questions_table.c.id == uuid.UUID(question_id),
                coding_questions_table.c.deleted_at.is_(None)
            )
        )
        result = self.session.execute(query).fetchone()

        if not result:
            return None

        question = dict(result._mapping)
        question["id"] = str(question["id"])
        question["organization_id"] = str(question["organization_id"])
        if question.get("created_by"):
            question["created_by"] = str(question["created_by"])

        # Hide solution unless explicitly requested
        if not include_solution:
            question.pop("solution", None)

        # Convert datetime objects to ISO strings
        for key in ["created_at", "updated_at", "deleted_at"]:
            if question.get(key):
                question[key] = question[key].isoformat()

        return question

    def get_questions_by_organization(
        self,
        organization_id: str,
        difficulty: str = None,
        tags: List[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get paginated list of coding questions for an organization (includes platform questions)
        
        If organization_id is None (admin), returns all questions across all organizations.
        """
        # Build query conditions
        conditions = [coding_questions_table.c.deleted_at.is_(None)]
        
        # If org_id provided, filter to that org + platform questions
        # If None (admin), show ALL questions
        if organization_id:
            conditions.append(
                or_(
                    coding_questions_table.c.organization_id == uuid.UUID(organization_id),
                    coding_questions_table.c.organization_id == PLATFORM_ORG_ID
                )
            )

        if difficulty:
            conditions.append(coding_questions_table.c.difficulty == difficulty)

        # Count total
        count_query = select(func.count()).select_from(coding_questions_table).where(and_(*conditions))
        total_count = self.session.execute(count_query).scalar()

        # Fetch paginated results
        offset = (page - 1) * page_size
        query = (
            select(coding_questions_table)
            .where(and_(*conditions))
            .order_by(coding_questions_table.c.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).fetchall()

        questions = []
        for row in results:
            q = dict(row._mapping)
            q["id"] = str(q["id"])
            q["organization_id"] = str(q["organization_id"])
            if q.get("created_by"):
                q["created_by"] = str(q["created_by"])
            # Don't include solution in list view
            q.pop("solution", None)
            for key in ["created_at", "updated_at", "deleted_at"]:
                if q.get(key):
                    q[key] = q[key].isoformat()
            questions.append(q)

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

        return {
            "questions": questions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

    def update_question(self, question_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update a coding question"""
        # Remove None values and set updated_at
        updates = {k: v for k, v in updates.items() if v is not None}
        updates["updated_at"] = datetime.utcnow()

        update_stmt = (
            coding_questions_table.update()
            .where(coding_questions_table.c.id == uuid.UUID(question_id))
            .values(**updates)
        )
        self.session.execute(update_stmt)

        return self.get_question(question_id)

    def delete_question(self, question_id: str) -> bool:
        """Soft delete a coding question"""
        update_stmt = (
            coding_questions_table.update()
            .where(coding_questions_table.c.id == uuid.UUID(question_id))
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = self.session.execute(update_stmt)
        return result.rowcount > 0

    def get_random_questions(
        self,
        organization_id: str,
        count: int = 1,
        difficulty: str = None,
        exclude_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get random active questions for an organization (includes platform questions)"""
        conditions = [
            or_(
                coding_questions_table.c.organization_id == uuid.UUID(organization_id),
                coding_questions_table.c.organization_id == PLATFORM_ORG_ID
            ),
            coding_questions_table.c.deleted_at.is_(None)
        ]

        if difficulty:
            conditions.append(coding_questions_table.c.difficulty == difficulty)

        if exclude_ids:
            conditions.append(
                ~coding_questions_table.c.id.in_([uuid.UUID(id) for id in exclude_ids])
            )

        query = (
            select(coding_questions_table)
            .where(and_(*conditions))
            .order_by(func.random())
            .limit(count)
        )
        results = self.session.execute(query).fetchall()

        questions = []
        for row in results:
            q = dict(row._mapping)
            q["id"] = str(q["id"])
            q["organization_id"] = str(q["organization_id"])
            if q.get("created_by"):
                q["created_by"] = str(q["created_by"])
            q.pop("solution", None)
            for key in ["created_at", "updated_at", "deleted_at"]:
                if q.get(key):
                    q[key] = q[key].isoformat()
            questions.append(q)

        return questions

    # ==========================================
    # CODING SESSIONS METHODS
    # ==========================================

    def create_session(
        self,
        interview_id: str,
        question_id: str,
        language: str = "python",
        starter_code: str = None
    ) -> Dict[str, Any]:
        """Create a new coding session for a candidate"""
        session_id = uuid.uuid4()
        now = datetime.utcnow()

        insert_stmt = coding_sessions_table.insert().values(
            id=session_id,
            interview_id=uuid.UUID(interview_id),
            question_id=uuid.UUID(question_id),
            language=language,
            code=starter_code,
            started_at=now,
            created_at=now
        )
        self.session.execute(insert_stmt)

        return {
            "id": str(session_id),
            "interview_id": interview_id,
            "question_id": question_id,
            "language": language,
            "code": starter_code,
            "started_at": now.isoformat()
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a coding session by ID"""
        query = select(coding_sessions_table).where(
            coding_sessions_table.c.id == uuid.UUID(session_id)
        )
        result = self.session.execute(query).fetchone()

        if not result:
            return None

        session = dict(result._mapping)
        # Convert UUIDs to strings
        for key in ["id", "interview_id", "question_id"]:
            if session.get(key):
                session[key] = str(session[key])

        # Convert datetime objects
        for key in ["started_at", "submitted_at", "created_at"]:
            if session.get(key):
                session[key] = session[key].isoformat()

        return session

    def get_sessions_by_interview(self, interview_id: str) -> List[Dict[str, Any]]:
        """Get coding sessions for an interview"""
        query = (
            select(coding_sessions_table)
            .where(coding_sessions_table.c.interview_id == uuid.UUID(interview_id))
            .order_by(coding_sessions_table.c.created_at.asc())
        )
        results = self.session.execute(query).fetchall()

        sessions = []
        for row in results:
            s = dict(row._mapping)
            for key in ["id", "interview_id", "question_id"]:
                if s.get(key):
                    s[key] = str(s[key])
            for key in ["started_at", "submitted_at", "created_at"]:
                if s.get(key):
                    s[key] = s[key].isoformat()
            sessions.append(s)

        return sessions

    def update_session_code(self, session_id: str, code: str) -> Optional[Dict[str, Any]]:
        """Update the code for a session (auto-save)"""
        update_stmt = (
            coding_sessions_table.update()
            .where(coding_sessions_table.c.id == uuid.UUID(session_id))
            .values(code=code)
        )
        self.session.execute(update_stmt)

        return self.get_session(session_id)

    def submit_session(
        self,
        session_id: str,
        code: str,
        execution_results: Dict[str, Any],
        is_correct: bool,
        execution_time: int = None,
        memory_usage: int = None
    ) -> Optional[Dict[str, Any]]:
        """Submit and evaluate a coding session"""
        now = datetime.utcnow()

        update_stmt = (
            coding_sessions_table.update()
            .where(coding_sessions_table.c.id == uuid.UUID(session_id))
            .values(
                code=code,
                execution_results=execution_results,
                is_correct=is_correct,
                execution_time=execution_time,
                memory_usage=memory_usage,
                submitted_at=now
            )
        )
        self.session.execute(update_stmt)

        return self.get_session(session_id)

    def get_session_stats(self, organization_id: str) -> Dict[str, Any]:
        """Get coding session statistics for an organization"""
        # Join with interviews to filter by organization
        from sqlalchemy import join

        # Get interviews for this org first
        interviews_subq = select(coding_sessions_table.c.id).select_from(
            coding_sessions_table.join(
                Table("interviews", metadata, autoload_with=self.session.bind),
                coding_sessions_table.c.interview_id == Table("interviews", metadata).c.id
            )
        ).where(
            Table("interviews", metadata).c.organization_id == uuid.UUID(organization_id)
        )

        # For simplicity, let's just count all sessions
        total_query = select(func.count()).select_from(coding_sessions_table)
        total = self.session.execute(total_query).scalar()

        # Submitted sessions
        submitted_query = select(func.count()).select_from(coding_sessions_table).where(
            coding_sessions_table.c.submitted_at.isnot(None)
        )
        submitted = self.session.execute(submitted_query).scalar()

        # Correct submissions
        correct_query = select(func.count()).select_from(coding_sessions_table).where(
            coding_sessions_table.c.is_correct == True
        )
        correct = self.session.execute(correct_query).scalar()

        return {
            "total_sessions": total,
            "submitted_sessions": submitted,
            "correct_submissions": correct,
            "success_rate": round(correct / submitted * 100, 1) if submitted > 0 else 0
        }

    # ==========================================
    # AI ANALYSIS METHODS (for assessment integration)
    # ==========================================

    def save_coding_to_ai_analysis(
        self,
        interview_id: str,
        coding_session_id: str,
        execution_results: Dict[str, Any],
        is_correct: bool,
        question_title: str = None
    ) -> str:
        """
        Save coding session results to ai_analysis table for assessment integration.

        Converts coding session results to the format expected by assessment service:
        - execution_results.correctness_score (0-100 scale)
        - execution_results.test_cases_passed
        - execution_results.test_cases_total
        """
        analysis_id = uuid.uuid4()
        now = datetime.utcnow()

        # Convert Judge0 results to assessment-compatible format
        score = execution_results.get('score', 0) * 100  # Convert 0-1 to 0-100
        passed_count = sum(1 for r in execution_results.get('results', []) if r.get('passed'))
        total_count = len(execution_results.get('results', []))

        raw_results = {
            'execution_results': {
                'correctness_score': score,
                'test_cases_passed': passed_count,
                'test_cases_total': total_count,
                'is_correct': is_correct,
                'question_title': question_title,
            },
            'code_quality': {
                'readability_score': 0,  # Could be enhanced with code analysis
            },
            'coding_session_id': coding_session_id,  # Store coding session reference here
            'original_results': execution_results,  # Keep original for reference
        }

        # session_id is NULL because ai_analysis.session_id references interview_sessions,
        # not coding_sessions. The coding_session_id is stored in raw_results instead.
        insert_stmt = ai_analysis_table.insert().values(
            id=analysis_id,
            interview_id=uuid.UUID(interview_id),
            session_id=None,
            analysis_type='coding_analysis',
            service_name='coding-service',
            raw_results=raw_results,
            confidence_score=1.0,  # Coding results are deterministic
            processing_time=int(execution_results.get('totalExecutionTime', 0) * 1000),
            version='1.0',
            created_at=now
        )
        self.session.execute(insert_stmt)

        return str(analysis_id)

    def check_coding_analysis_exists(self, interview_id: str, session_id: str) -> bool:
        """Check if coding analysis already exists for this session"""
        query = select(ai_analysis_table).where(
            and_(
                ai_analysis_table.c.interview_id == uuid.UUID(interview_id),
                ai_analysis_table.c.session_id == uuid.UUID(session_id),
                ai_analysis_table.c.service_name == 'coding-service'
            )
        )
        result = self.session.execute(query).fetchone()
        return result is not None

    # ==========================================
    # INTERVIEW STATUS METHODS
    # ==========================================

    def update_interview_status(self, interview_id: str, status: str) -> bool:
        """Update interview status and completed_at timestamp"""
        from sqlalchemy import update as sql_update

        values = {'status': status}
        if status == 'completed':
            values['completed_at'] = datetime.utcnow()

        update_stmt = (
            sql_update(interviews_table)
            .where(interviews_table.c.id == uuid.UUID(interview_id))
            .values(**values)
        )
        result = self.session.execute(update_stmt)
        return result.rowcount > 0
