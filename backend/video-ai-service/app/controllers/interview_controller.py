"""
Interview Video Processing Controller

Endpoints for processing interview videos asynchronously
"""
from fastapi import APIRouter, HTTPException, status
import sys
sys.path.append('/common-service')

from db import UnitOfWork
from app.core.logging import get_logger
from app.schemas.interview_schemas import ProcessInterviewVideoRequest, ProcessInterviewVideoResponse
from app.repositories.video_repository import VideoRepository
from app.services.interview_video_processing_service import InterviewVideoProcessingService

logger = get_logger("interview_controller")
router = APIRouter(prefix="/interview", tags=["interview"])


@router.post(
    "/process-interview-video",
    response_model=ProcessInterviewVideoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process interview video (async)",
    description="""
    Process interview video with complete analysis pipeline.

    **Flow:**
    1. Receives request with interview IDs, media file ID and session ID
    2. Returns 202 Accepted immediately
    3. Processes in background (5-10 minutes)
    4. Updates media_files.status and saves results

    **Called by:** Orchestration Service after candidate submits answer
    """
)
async def process_interview_video_endpoint(request: ProcessInterviewVideoRequest):
    """
    Main API endpoint for interview video processing

    Validates request and starts background processing
    Returns immediately (asynchronous)
    """
    logger.info("📹 Video processing request received")
    logger.info(f"   Interview: {request.interview_id}")
    logger.info(f"   Session: {request.session_id}")
    logger.info(f"   Media File: {request.media_file_id}")

    try:
        # Validate: Check if media file exists
        uow = UnitOfWork()
        repo = VideoRepository(uow)

        media_file = repo.get_media_file_by_id(str(request.media_file_id))

        if not media_file:
            logger.error(f"❌ Media file not found: {request.media_file_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media file {request.media_file_id} not found"
            )

        # Extract storage_uri from media_file record
        storage_uri = media_file.get('storage_uri') if isinstance(media_file, dict) else media_file.storage_uri

        if not storage_uri:
            logger.error(f"❌ Storage URI missing for media file: {request.media_file_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage URI missing for media file {request.media_file_id}"
            )

        logger.info(f"📂 storage_uri: {storage_uri}")

        # Check if already processed (idempotency)
        if repo.check_if_already_processed(
            str(request.interview_id),
            str(request.session_id)
        ):
            logger.warning("⚠️ Already processed - returning success")
            return ProcessInterviewVideoResponse(
                status="accepted",
                message="Already processed (idempotent)",
                media_file_id=str(request.media_file_id),
                interview_id=str(request.interview_id),
                session_id=str(request.session_id)
            )

        # Start background processing via service layer
        processing_service = InterviewVideoProcessingService()
        processing_service.process_async(
            interview_id=str(request.interview_id),
            session_id=str(request.session_id),
            media_file_id=str(request.media_file_id),
            storage_uri=storage_uri
        )

        logger.info("✅ Background processing started")

        # Return immediate response
        return ProcessInterviewVideoResponse(
            status="accepted",
            message="Video processing started in background",
            media_file_id=str(request.media_file_id),
            interview_id=str(request.interview_id),
            session_id=str(request.session_id)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Failed to start processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start video processing: {str(e)}"
        )
