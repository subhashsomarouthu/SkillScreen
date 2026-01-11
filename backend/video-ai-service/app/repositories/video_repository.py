"""
Video Repository for database operations
"""
import sys
sys.path.append('/common-service')

from repository.base_repository import BaseRepository
from db import UnitOfWork
from sqlalchemy import Table, Column, String, DateTime, MetaData, select, insert, update, and_
from sqlalchemy.dialects.postgresql import UUID, JSONB, NUMERIC, BIGINT
from datetime import datetime, timezone
from typing import Dict, Optional
import json


metadata = MetaData()

# Table definitions
media_files_table = Table(
    "media_files",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("interview_id", UUID),
    Column("session_id", UUID),
    Column("file_type", String),
    Column("storage_uri", String),
    Column("file_size", BIGINT),
    Column("duration", BIGINT),
    Column("mime_type", String),
    Column("checksum", String),
    Column("metadata", JSONB),
    Column("created_at", DateTime),
    Column("deleted_at", DateTime),
    Column("blob_name", String),
    Column("expected_total", BIGINT),
    Column("received_indices", JSONB),
    Column("status", String),
    Column("updated_at", DateTime),
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
    Column("processing_time", BIGINT),
    Column("version", String),
    Column("created_at", DateTime),
)


class VideoRepository(BaseRepository):
    """Repository for video analysis operations"""

    def __init__(self, uow: UnitOfWork):
        super().__init__(uow)
        self.media_files_table = media_files_table
        self.ai_analysis_table = ai_analysis_table

    def get_media_file_by_id(self, media_file_id: str) -> Optional[Dict]:
        """Get media file record by ID"""
        stmt = select(self.media_files_table).where(
            self.media_files_table.c.id == media_file_id
        )
        result = self.uow.session.execute(stmt).fetchone()
        return dict(result._mapping) if result else None

    def update_media_file_status(self, media_file_id: str, status: str):
        """Update media file status"""
        stmt = (
            update(self.media_files_table)
            .where(self.media_files_table.c.id == media_file_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        self.uow.session.execute(stmt)
        self.uow.session.commit()

    def save_video_analysis(
        self,
        interview_id: str,
        session_id: str,
        analysis_data: Dict,
        confidence_score: float = None,
        processing_time: int = 0
    ):
        """Save video analysis results to ai_analysis table"""
        stmt = insert(self.ai_analysis_table).values(
            interview_id=interview_id,
            session_id=session_id,
            analysis_type="video",
            service_name="video-ai-service",
            raw_results=json.dumps(analysis_data),
            confidence_score=confidence_score,
            processing_time=processing_time,
            version="1.0.0",
            created_at=datetime.now(timezone.utc)
        )
        self.uow.session.execute(stmt)
        self.uow.session.commit()

    def check_if_already_processed(self, interview_id: str, session_id: str) -> bool:
        """Check if video analysis already exists for this session (idempotency)"""
        stmt = select(self.ai_analysis_table).where(
            and_(
                self.ai_analysis_table.c.interview_id == interview_id,
                self.ai_analysis_table.c.session_id == session_id,
                self.ai_analysis_table.c.analysis_type == "video"
            )
        )
        result = self.uow.session.execute(stmt).fetchone()
        return result is not None
