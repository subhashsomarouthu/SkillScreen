import sys
sys.path.append('/common-service')

from repository.base_repository import BaseRepository
from db import UnitOfWork
from sqlalchemy import Table, Column, Text, Integer, String, Boolean, DateTime, MetaData, select, insert, update, text, and_, cast
from sqlalchemy.dialects.postgresql import UUID, JSONB, NUMERIC
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import json


metadata = MetaData()

# ==========================================
# TABLE DEFINITIONS
# ==========================================

interviews_table = Table(
    "interviews",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID),
    Column("job_position_id", UUID),
    Column("candidate_id", UUID),
    Column("interviewer_id", UUID),
    Column("template_id", UUID),
    Column("status", String),
    Column("mode", String),
    Column("scheduled_at", DateTime),
    Column("started_at", DateTime),
    Column("completed_at", DateTime),
    Column("settings", JSONB),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    Column("deleted_at", DateTime),
)

interview_sessions_table = Table(
    "interview_sessions",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("interview_id", UUID),
    Column("question_id", String),
    Column("question_text", Text),
    Column("question_type", String),
    Column("candidate_response", Text),
    Column("response_duration", Integer),
    Column("started_at", DateTime),
    Column("completed_at", DateTime),
    Column("metadata", JSONB),
    Column("created_at", DateTime),
)

ai_analysis_table = Table(
    "ai_analysis",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("interview_id", UUID),
    Column("session_id", UUID),
    Column("analysis_type", String),
    Column("service_name", String),
    Column("raw_results", JSONB),
    Column("confidence_score", NUMERIC),
    Column("processing_time", Integer),
    Column("version", String),
    Column("created_at", DateTime),
)

assessments_table = Table(
    "assessments",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("interview_id", UUID),
    Column("overall_score", NUMERIC(5, 2)),
    Column("hard_skills_score", NUMERIC(5, 2)),
    Column("soft_skills_score", NUMERIC(5, 2)),
    Column("communication_score", NUMERIC(5, 2)),
    Column("technical_score", NUMERIC(5, 2)),
    Column("proctoring_risk_score", NUMERIC(5, 2)),
    Column("recommendation", String),  # hire, no_hire, maybe, needs_review
    Column("evidence_clips", JSONB),
    Column("summary", Text),
    Column("reviewer_notes", Text),
    Column("reviewed_by", UUID),
    Column("reviewed_at", DateTime),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    Column("deleted_at", DateTime),
)

job_positions_table = Table(
    "job_positions",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID),
    Column("title", String),
    Column("description", Text),
    Column("required_skills", JSONB),
    Column("department", String),
    Column("is_active", Boolean),
    Column("created_by", UUID),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    Column("deleted_at", DateTime),
)

candidates_table = Table(
    "candidates",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID),
    Column("email", String),
    Column("full_name", String),
    Column("phone", String),
    Column("resume_url", String),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)


# ==========================================
# REPOSITORY CLASS
# ==========================================

class AssessmentRepository(BaseRepository):
    """Repository for assessment orchestration database operations"""

    def __init__(self, session_or_uow):
        """
        Initialize repository with session or UnitOfWork

        Args:
            session_or_uow: Either a SQLAlchemy Session or UnitOfWork object
        """
        if hasattr(session_or_uow, 'session'):
            self.session = session_or_uow.session
        else:
            self.session = session_or_uow

    def _fetch_one(self, query) -> Optional[Dict]:
        """Helper to fetch one row and convert to dict"""
        result = self.session.execute(query).fetchone()
        return dict(result._mapping) if result else None

    def _fetch_all(self, query) -> List[Dict]:
        """Helper to fetch all rows and convert to list of dicts"""
        result = self.session.execute(query)
        return [dict(row._mapping) for row in result]

    def _parse_raw_results(self, raw_results) -> Dict:
        """
        Parse raw_results field, handling both dict and double-serialized string cases.

        Some older records may have raw_results stored as JSON string instead of JSONB dict
        due to incorrect use of json.dumps() when saving.
        """
        if raw_results is None:
            return {}
        if isinstance(raw_results, dict):
            return raw_results
        if isinstance(raw_results, str):
            try:
                return json.loads(raw_results)
            except json.JSONDecodeError:
                return {}
        return {}
    
    # ==========================================
    # FIND READY INTERVIEWS
    # ==========================================
    
    def get_completed_interviews_without_assessment(self, limit: int = 10) -> List[Dict]:
        """
        Get interviews that are completed but don't have assessments yet
        Also applies grace period filter (completed > 5 minutes ago)
        
        Returns:
            List of interview records ready for assessment
        """
        from config.settings import settings
        
        grace_period_minutes = settings.assessment_grace_period_minutes
        
        query = text(f"""
            SELECT i.id, i.organization_id, i.job_position_id, i.candidate_id, 
                   i.completed_at, i.settings
            FROM interviews i
            LEFT JOIN assessments a ON i.id = a.interview_id
            WHERE i.status = 'completed'
              AND a.id IS NULL
              AND i.completed_at < NOW() - INTERVAL '{grace_period_minutes} minutes'
            ORDER BY i.completed_at ASC
            LIMIT :limit
        """)
        
        result = self.session.execute(query, {"limit": limit})
        interviews = [dict(row._mapping) for row in result]
        
        return interviews
    
    # ==========================================
    # VERIFY ALL SERVICES COMPLETED
    # ==========================================
    
    def get_all_sessions_for_interview(self, interview_id: str) -> List[Dict]:
        """Get all sessions for an interview"""
        query = select(interview_sessions_table).where(
            interview_sessions_table.c.interview_id == interview_id
        ).order_by(interview_sessions_table.c.created_at)

        return self._fetch_all(query)
    
    def check_session_has_service_analysis(
        self, 
        interview_id: str, 
        session_id: str, 
        service_name: str
    ) -> bool:
        """
        Check if a specific service has completed analysis for a session
        
        Args:
            interview_id: Interview UUID
            session_id: Session UUID
            service_name: 'audio-ai-service', 'video-ai-service', 'text-service'
        
        Returns:
            True if service analysis exists, False otherwise
        """
        query = select(ai_analysis_table).where(
            and_(
                ai_analysis_table.c.interview_id == interview_id,
                ai_analysis_table.c.session_id == session_id,
                ai_analysis_table.c.service_name == service_name
            )
        )
        
        result = self.session.execute(query).fetchone()
        return result is not None
    
    def check_coding_analysis_exists(self, interview_id: str) -> bool:
        """Check if coding analysis exists for interview"""
        query = select(ai_analysis_table).where(
            and_(
                ai_analysis_table.c.interview_id == interview_id,
                ai_analysis_table.c.service_name == 'coding-service'
            )
        )
        
        result = self.session.execute(query).fetchone()
        return result is not None
    
    def _check_template_sessions(self, interview_id: str, template_id: str) -> bool:
        """Check if all template questions have sessions"""
        expected_question_count = self._get_template_question_count(str(template_id))
        actual_session_count = len(self.get_all_sessions_for_interview(interview_id))
        return expected_question_count <= 0 or actual_session_count >= expected_question_count

    def _check_all_session_services(self, interview_id: str, sessions: List[Dict]) -> bool:
        """Check if all required services completed for all sessions"""
        required_services = ['audio-ai-service', 'video-ai-service', 'text-service']

        for session in sessions:
            session_id = str(session['id'])
            for service_name in required_services:
                if not self.check_session_has_service_analysis(interview_id, session_id, service_name):
                    return False
        return True

    def all_services_completed(self, interview_id: str) -> bool:
        """
        Check if all required AI services have completed for ALL sessions

        Returns:
            True if all services complete, False otherwise
        """
        # Get interview info first
        interview = self.get_interview_info(interview_id)
        if not interview:
            return False

        # Check if all template questions have sessions
        template_id = interview.get('template_id')
        if template_id and not self._check_template_sessions(interview_id, template_id):
            return False

        # Get and validate sessions
        sessions = self.get_all_sessions_for_interview(interview_id)
        if not sessions:
            return False

        # Check all session services
        if not self._check_all_session_services(interview_id, sessions):
            return False

        # Check coding if required
        settings = interview.get('settings') or {}
        requires_coding = settings.get('requires_coding', False)

        if requires_coding and not self.check_coding_analysis_exists(interview_id):
            return False

        return True
    
    def _ensure_timezone_aware(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime is timezone-aware"""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _check_template_mismatch(
        self,
        interview_id: str,
        template_id: str,
        actual_session_count: int,
        interview_completed_at: datetime,
        timeout_threshold: datetime,
        result: dict,
        logger
    ) -> bool:
        """Check template mismatch and return True if should continue processing"""
        expected_question_count = self._get_template_question_count(str(template_id))

        if expected_question_count <= 0 or actual_session_count >= expected_question_count:
            return True

        result['template_mismatch'] = True
        result['all_complete'] = False

        if interview_completed_at < timeout_threshold:
            logger.warning(
                "template_session_mismatch_timed_out",
                interview_id=interview_id,
                expected=expected_question_count,
                actual=actual_session_count,
                completed_at=interview_completed_at
            )
            result['stuck_sessions'].append('__template_mismatch__')
        else:
            logger.info(
                "template_session_mismatch_within_grace_period",
                interview_id=interview_id,
                expected=expected_question_count,
                actual=actual_session_count
            )
            return False

        return True

    def _process_session_services(
        self,
        interview_id: str,
        session_id: str,
        session_completed_at: datetime,
        timeout_threshold: datetime,
        result: dict,
        logger
    ):
        """Check services for a session and update result"""
        required_services = ['audio-ai-service', 'video-ai-service', 'text-service']

        for service_name in required_services:
            if self.check_session_has_service_analysis(interview_id, session_id, service_name):
                continue

            result['all_complete'] = False

            if session_completed_at < timeout_threshold:
                if session_id not in result['stuck_sessions']:
                    result['stuck_sessions'].append(session_id)
                    logger.warning(
                        "session_timed_out",
                        interview_id=interview_id,
                        session_id=session_id,
                        service_name=service_name,
                        completed_at=session_completed_at,
                        timeout_threshold=timeout_threshold
                    )
            else:
                if session_id not in result['missing_sessions']:
                    result['missing_sessions'].append(session_id)
                    logger.info(
                        "session_processing",
                        interview_id=interview_id,
                        session_id=session_id,
                        service_name=service_name,
                        completed_at=session_completed_at
                    )

    def _check_coding_service(
        self,
        interview_id: str,
        settings: dict,
        interview_completed_at: datetime,
        timeout_threshold: datetime,
        result: dict,
        logger
    ):
        """Check coding service if required"""
        if not settings.get('requires_coding', False):
            return

        if self.check_coding_analysis_exists(interview_id):
            return

        result['all_complete'] = False

        if interview_completed_at < timeout_threshold:
            result['stuck_sessions'].append('__coding_service__')
            logger.warning(
                "coding_service_timed_out",
                interview_id=interview_id,
                completed_at=interview_completed_at
            )
        else:
            result['missing_sessions'].append('__coding_service__')
            logger.info("coding_service_processing", interview_id=interview_id)

    def _log_final_result(self, interview_id: str, result: dict, logger):
        """Log final processing result"""
        if result['all_complete']:
            logger.info("all_services_completed", interview_id=interview_id)
        elif result['stuck_sessions']:
            logger.warning(
                "partial_assessment_ready",
                interview_id=interview_id,
                stuck_count=len(result['stuck_sessions']),
                stuck_sessions=result['stuck_sessions']
            )
        else:
            logger.info(
                "services_still_processing",
                interview_id=interview_id,
                missing_count=len(result['missing_sessions'])
            )

    def check_sessions_with_timeout(self, interview_id: str, timeout_minutes: int = 30) -> dict:
        """
        Check AI service completion with timeout logic

        This method handles three scenarios:
        1. All services completed → all_complete = True
        2. Services incomplete but within timeout → all_complete = False, empty stuck_sessions (still processing)
        3. Services incomplete and timed out → all_complete = False, with stuck_sessions (generate partial assessment)

        Args:
            interview_id: Interview UUID
            timeout_minutes: Minutes to wait before considering session stuck (default: 30)

        Returns:
            {
                'all_complete': bool,
                'stuck_sessions': list of session IDs that timed out,
                'missing_sessions': list of incomplete sessions (no timeout yet),
                'template_mismatch': bool (if expected questions != actual sessions)
            }
        """
        from config.logger import logger

        result = {
            'all_complete': True,
            'stuck_sessions': [],
            'missing_sessions': [],
            'template_mismatch': False
        }

        # Get interview info
        interview = self.get_interview_info(interview_id)
        if not interview:
            result['all_complete'] = False
            logger.error("interview_not_found_in_timeout_check", interview_id=interview_id)
            return result

        # Get interview completion time
        interview_completed_at = interview.get('completed_at')
        if not interview_completed_at:
            result['all_complete'] = False
            logger.warning("interview_not_completed_yet", interview_id=interview_id)
            return result

        interview_completed_at = self._ensure_timezone_aware(interview_completed_at)
        timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        # Get sessions and check template
        actual_sessions = self.get_all_sessions_for_interview(interview_id)
        actual_session_count = len(actual_sessions)

        template_id = interview.get('template_id')
        if template_id and not self._check_template_mismatch(
            interview_id, template_id, actual_session_count,
            interview_completed_at, timeout_threshold, result, logger
        ):
            return result

        if not actual_sessions:
            result['all_complete'] = False
            logger.warning("no_sessions_found", interview_id=interview_id)
            return result

        # Check each session
        for session in actual_sessions:
            session_id = str(session['id'])
            session_completed_at = session.get('completed_at')

            if not session_completed_at:
                result['all_complete'] = False
                result['missing_sessions'].append(session_id)
                logger.info(
                    "session_not_completed",
                    interview_id=interview_id,
                    session_id=session_id
                )
                continue

            session_completed_at = self._ensure_timezone_aware(session_completed_at)
            self._process_session_services(
                interview_id, session_id, session_completed_at,
                timeout_threshold, result, logger
            )

        # Check coding service
        settings = interview.get('settings') or {}
        self._check_coding_service(
            interview_id, settings, interview_completed_at,
            timeout_threshold, result, logger
        )

        # Log result
        self._log_final_result(interview_id, result, logger)

        return result
    
    def _get_template_question_count(self, template_id: str) -> int:
        """Get number of questions in template"""
        from sqlalchemy import Table, Column, Text, MetaData, select
        from sqlalchemy.dialects.postgresql import UUID, JSONB
        
        metadata = MetaData()
        interview_templates_table = Table(
            "interview_templates",
            metadata,
            Column("id", UUID, primary_key=True),
            Column("questions", JSONB),
        )
        
        query = select(interview_templates_table.c.questions).where(
            interview_templates_table.c.id == template_id
        )
        
        result = self.session.execute(query).fetchone()
        
        if result and result[0]:
            questions = result[0]
            if isinstance(questions, list):
                return len(questions)
        
        return 0
    
    # ==========================================
    # GET AI ANALYSIS RESULTS
    # ==========================================

    def get_all_ai_analysis_for_interview(self, interview_id: str) -> List[Dict]:
        """Get all AI analysis results for an interview"""
        query = select(ai_analysis_table).where(
            ai_analysis_table.c.interview_id == interview_id
        ).order_by(ai_analysis_table.c.created_at)

        results = self._fetch_all(query)
        # Parse raw_results to handle double-serialized JSON from older records
        for result in results:
            result['raw_results'] = self._parse_raw_results(result.get('raw_results'))
        return results

    def get_ai_analysis_by_service(
        self,
        interview_id: str,
        service_name: str
    ) -> List[Dict]:
        """Get all AI analysis results for a specific service"""
        query = select(ai_analysis_table).where(
            and_(
                ai_analysis_table.c.interview_id == interview_id,
                ai_analysis_table.c.service_name == service_name
            )
        ).order_by(ai_analysis_table.c.created_at)

        results = self._fetch_all(query)
        # Parse raw_results to handle double-serialized JSON from older records
        for result in results:
            result['raw_results'] = self._parse_raw_results(result.get('raw_results'))
        return results
    
    # ==========================================
    # INTERVIEW & JOB POSITION INFO
    # ==========================================
    
    def get_interview_info(self, interview_id: str) -> Optional[Dict]:
        """Get interview details"""
        query = select(interviews_table).where(
            interviews_table.c.id == interview_id
        )

        return self._fetch_one(query)

    def get_job_position(self, job_position_id: str) -> Optional[Dict]:
        """Get job position details (for job description)"""
        query = select(job_positions_table).where(
            job_positions_table.c.id == job_position_id
        )

        return self._fetch_one(query)
    
    # ==========================================
    # CHECK IF ASSESSMENT ALREADY EXISTS
    # ==========================================
    
    def assessment_exists(self, interview_id: str) -> bool:
        """Check if assessment already exists for interview"""
        query = select(assessments_table).where(
            assessments_table.c.interview_id == interview_id
        )

        return self._fetch_one(query) is not None

    def get_assessment(self, interview_id: str) -> Optional[Dict]:
        """Get existing assessment for interview"""
        query = select(assessments_table).where(
            assessments_table.c.interview_id == interview_id
        )

        return self._fetch_one(query)
    
    # ==========================================
    # SAVE ASSESSMENT
    # ==========================================
    
    def save_assessment(self, data: Dict) -> str:
        """
        Save final assessment to database
        
        Args:
            data: Assessment data including all scores and recommendation
        
        Returns:
            Assessment ID
        """
        if 'created_at' not in data:
            data['created_at'] = datetime.now(timezone.utc)
        
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now(timezone.utc)
        
        query = insert(assessments_table).values(**data)
        result = self.session.execute(query)
        self.session.commit()
        
        assessment_id = result.inserted_primary_key[0]
        return str(assessment_id)
    
    def update_assessment(self, interview_id: str, data: Dict):
        """Update existing assessment"""
        data['updated_at'] = datetime.now(timezone.utc)

        query = update(assessments_table).where(
            assessments_table.c.interview_id == interview_id
        ).values(**data)

        self.session.execute(query)
        self.session.commit()

    # ==========================================
    # RECRUITER DASHBOARD METHODS
    # ==========================================

    def get_dashboard_candidates(
        self,
        organization_id: Optional[str] = None,
        job_position_id: Optional[str] = None,
        recommendation: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict:
        """
        Get candidates for recruiter dashboard with filtering and pagination.

        Returns both assessed and pending candidates.

        Args:
            organization_id: Filter by organization
            job_position_id: Filter by job position
            recommendation: Filter by recommendation (hire, no_hire, maybe, needs_review)
            status: Filter by status (assessed, pending, processing)
            min_score: Minimum overall score filter
            max_score: Maximum overall score filter
            page: Page number (1-indexed)
            page_size: Number of items per page
            sort_by: Field to sort by (overall_score, created_at, name)
            sort_order: Sort order (asc, desc)

        Returns:
            Dict with candidates list, pagination info, and summary stats
        """
        from sqlalchemy import func, case, literal_column
        from sqlalchemy.sql import label

        # Build base query joining interviews, candidates, job_positions, and assessments
        base_query = (
            select(
                interviews_table.c.id.label("interview_id"),
                interviews_table.c.candidate_id,
                interviews_table.c.job_position_id,
                interviews_table.c.status.label("interview_status"),
                interviews_table.c.completed_at,
                interviews_table.c.created_at.label("interview_created_at"),
                candidates_table.c.full_name.label("candidate_name"),
                candidates_table.c.email.label("candidate_email"),
                job_positions_table.c.title.label("job_title"),
                assessments_table.c.id.label("assessment_id"),
                assessments_table.c.overall_score,
                assessments_table.c.recommendation,
                assessments_table.c.technical_score,
                assessments_table.c.communication_score,
                assessments_table.c.soft_skills_score,
                assessments_table.c.proctoring_risk_score,
                assessments_table.c.created_at.label("assessment_created_at"),
            )
            .select_from(interviews_table)
            .outerjoin(candidates_table, interviews_table.c.candidate_id == candidates_table.c.id)
            .outerjoin(job_positions_table, interviews_table.c.job_position_id == job_positions_table.c.id)
            .outerjoin(assessments_table, interviews_table.c.id == assessments_table.c.interview_id)
            .where(interviews_table.c.deleted_at.is_(None))
        )

        # Apply filters
        if organization_id:
            # Cast string to UUID for proper comparison with UUID column
            base_query = base_query.where(interviews_table.c.organization_id == cast(organization_id, UUID))

        if job_position_id:
            base_query = base_query.where(interviews_table.c.job_position_id == cast(job_position_id, UUID))

        if recommendation:
            base_query = base_query.where(assessments_table.c.recommendation == recommendation)

        if status:
            if status == "assessed":
                base_query = base_query.where(assessments_table.c.id.isnot(None))
            elif status == "pending":
                base_query = base_query.where(
                    and_(
                        assessments_table.c.id.is_(None),
                        interviews_table.c.status == "completed"
                    )
                )
            elif status == "in_progress":
                base_query = base_query.where(interviews_table.c.status == "in_progress")

        if min_score is not None:
            base_query = base_query.where(assessments_table.c.overall_score >= min_score)

        if max_score is not None:
            base_query = base_query.where(assessments_table.c.overall_score <= max_score)

        # Get total count before pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = self.session.execute(count_query).scalar() or 0

        # Apply sorting
        sort_column = {
            "overall_score": assessments_table.c.overall_score,
            "created_at": interviews_table.c.created_at,
            "name": candidates_table.c.full_name,
            "recommendation": assessments_table.c.recommendation,
        }.get(sort_by, interviews_table.c.created_at)

        if sort_order == "asc":
            base_query = base_query.order_by(sort_column.asc().nullslast())
        else:
            base_query = base_query.order_by(sort_column.desc().nullsfirst())

        # Apply pagination
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # Execute query
        results = self._fetch_all(base_query)

        # Transform results
        candidates = []
        for row in results:
            has_assessment = row.get("assessment_id") is not None
            candidate_status = "assessed" if has_assessment else (
                "pending" if row.get("interview_status") == "completed" else row.get("interview_status")
            )

            candidates.append({
                "interview_id": str(row["interview_id"]) if row["interview_id"] else None,
                "candidate_id": str(row["candidate_id"]) if row["candidate_id"] else None,
                "candidate_name": row.get("candidate_name") or "Unknown",
                "candidate_email": row.get("candidate_email"),
                "job_position_id": str(row["job_position_id"]) if row["job_position_id"] else None,
                "job_title": row.get("job_title") or "Unknown Position",
                "status": candidate_status,
                "interview_completed_at": row["completed_at"].isoformat() if row.get("completed_at") else None,
                "assessment": {
                    "id": str(row["assessment_id"]) if row.get("assessment_id") else None,
                    "overall_score": float(row["overall_score"]) if row.get("overall_score") else None,
                    "recommendation": row.get("recommendation"),
                    "technical_score": float(row["technical_score"]) if row.get("technical_score") else None,
                    "communication_score": float(row["communication_score"]) if row.get("communication_score") else None,
                    "soft_skills_score": float(row["soft_skills_score"]) if row.get("soft_skills_score") else None,
                    "proctoring_risk_score": float(row["proctoring_risk_score"]) if row.get("proctoring_risk_score") else None,
                    "created_at": row["assessment_created_at"].isoformat() if row.get("assessment_created_at") else None,
                } if has_assessment else None
            })

        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size

        return {
            "candidates": candidates,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

    def get_dashboard_stats(self, organization_id: Optional[str] = None, job_position_id: Optional[str] = None) -> Dict:
        """
        Get summary statistics for recruiter dashboard.

        Args:
            organization_id: Filter by organization
            job_position_id: Filter by job position

        Returns:
            Dict with summary statistics
        """
        from sqlalchemy import func

        # Base filters
        interview_filter = [interviews_table.c.deleted_at.is_(None)]
        if organization_id:
            # Cast string to UUID for proper comparison with UUID column
            interview_filter.append(interviews_table.c.organization_id == cast(organization_id, UUID))
        if job_position_id:
            interview_filter.append(interviews_table.c.job_position_id == cast(job_position_id, UUID))

        # Total interviews
        total_query = select(func.count(interviews_table.c.id)).where(and_(*interview_filter))
        total_interviews = self.session.execute(total_query).scalar() or 0

        # Completed interviews
        completed_query = select(func.count(interviews_table.c.id)).where(
            and_(*interview_filter, interviews_table.c.status == "completed")
        )
        completed_interviews = self.session.execute(completed_query).scalar() or 0

        # Interviews with assessments
        assessed_query = (
            select(func.count(interviews_table.c.id))
            .select_from(interviews_table)
            .join(assessments_table, interviews_table.c.id == assessments_table.c.interview_id)
            .where(and_(*interview_filter))
        )
        assessed_count = self.session.execute(assessed_query).scalar() or 0

        # Pending (completed but no assessment)
        pending_count = completed_interviews - assessed_count

        # Recommendation breakdown
        recommendation_query = (
            select(
                assessments_table.c.recommendation,
                func.count(assessments_table.c.id).label("count")
            )
            .select_from(assessments_table)
            .join(interviews_table, assessments_table.c.interview_id == interviews_table.c.id)
            .where(and_(*interview_filter))
            .group_by(assessments_table.c.recommendation)
        )
        recommendation_results = self.session.execute(recommendation_query).fetchall()
        recommendations = {row[0]: row[1] for row in recommendation_results}

        # Average scores
        avg_query = (
            select(
                func.avg(assessments_table.c.overall_score).label("avg_overall"),
                func.avg(assessments_table.c.technical_score).label("avg_technical"),
                func.avg(assessments_table.c.communication_score).label("avg_communication"),
                func.avg(assessments_table.c.soft_skills_score).label("avg_soft_skills"),
            )
            .select_from(assessments_table)
            .join(interviews_table, assessments_table.c.interview_id == interviews_table.c.id)
            .where(and_(*interview_filter))
        )
        avg_result = self.session.execute(avg_query).fetchone()

        return {
            "total_interviews": total_interviews,
            "completed_interviews": completed_interviews,
            "assessed_count": assessed_count,
            "pending_count": pending_count,
            "in_progress_count": total_interviews - completed_interviews,
            "recommendations": {
                "hire": recommendations.get("hire", 0),
                "no_hire": recommendations.get("no_hire", 0),
                "maybe": recommendations.get("maybe", 0),
                "needs_review": recommendations.get("needs_review", 0),
            },
            "average_scores": {
                "overall": round(float(avg_result[0]), 2) if avg_result and avg_result[0] else None,
                "technical": round(float(avg_result[1]), 2) if avg_result and avg_result[1] else None,
                "communication": round(float(avg_result[2]), 2) if avg_result and avg_result[2] else None,
                "soft_skills": round(float(avg_result[3]), 2) if avg_result and avg_result[3] else None,
            }
        }