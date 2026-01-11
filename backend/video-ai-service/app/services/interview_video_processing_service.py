"""
Interview Video Processing Service

Handles background processing of interview videos:
- Downloads video from Azure Blob Storage
- Runs video analysis (face, emotions, gaze, etc.)
- Saves results to ai_analysis table
- Updates media_files status

Used by: interview_controller.py for the /process-interview-video endpoint
"""
import threading
import os
import json
import tempfile
import requests
from typing import Dict, Optional
from datetime import datetime, timezone
import sys
sys.path.append('/common-service')

from db import UnitOfWork
from app.repositories.video_repository import VideoRepository
from app.core.logging import get_logger
from app.services.analysis_service import _ensure_models, _make_analyzer

logger = get_logger("interview_video_processing")


class InterviewVideoProcessingService:
    """
    Service for processing interview videos with database integration

    This service orchestrates:
    - Status updates in media_files table
    - Video download from Azure
    - Video processing pipeline
    - Result persistence to database
    """

    def __init__(self):
        self.max_retries = 2  # Allow up to 3 attempts

    def _download_video(self, storage_uri: str, media_file_id: str, interview_id: str, blob_name: str = None) -> Optional[str]:
        """
        Download video from storage URI (Azure Blob or local path)

        Args:
            storage_uri: URI to video (e.g., /video/... or https://...)
            media_file_id: Media file ID for temp file naming
            interview_id: Interview ID for local path construction
            blob_name: Actual filename from database (e.g., "interview_id_hash_response.webm")

        Returns:
            Path to downloaded video file, or None if failed
        """
        try:
            # Check if it's a local path (starts with /)
            if storage_uri.startswith("/"):
                # Local path - use blob_name to construct actual file path
                # Files are saved to /app/temp/uploads/{interview_id}/{blob_name}
                if blob_name:
                    local_path = f"/app/temp/uploads/{interview_id}/{blob_name}"
                else:
                    # Fallback if blob_name not provided
                    local_path = f"/app/temp/uploads{storage_uri}".replace("/video/", "/", 1)

                if os.path.exists(local_path):
                    logger.info(f"Using local video path: {local_path}")
                    return local_path
                else:
                    logger.warning(f"Local path not found: {local_path}, trying as URL")

            # It's a URL (Azure Blob or HTTP)
            logger.info(f"Downloading from URL: {storage_uri}")

            # Create temp directory for downloads
            temp_dir = tempfile.gettempdir()
            video_filename = f"{media_file_id}.webm"
            video_path = os.path.join(temp_dir, video_filename)

            # Download the video
            response = requests.get(storage_uri, stream=True, timeout=300)
            response.raise_for_status()

            # Save to temp file
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"✅ Video downloaded: {video_path} ({os.path.getsize(video_path)} bytes)")
            return video_path

        except Exception as e:
            logger.error(f"❌ Video download failed: {str(e)}")
            return None

    def process_async(
        self,
        interview_id: str,
        session_id: str,
        media_file_id: str,
        storage_uri: str
    ):
        """
        Start asynchronous video processing in background thread

        Args:
            interview_id: Interview UUID
            session_id: Session UUID (question)
            media_file_id: Media file UUID
            storage_uri: Azure blob storage URI
        """
        logger.info(f"🚀 Starting async video processing for media file {media_file_id}")

        # Start background thread
        processing_thread = threading.Thread(
            target=self._process_background,
            args=(interview_id, session_id, media_file_id, storage_uri),
            daemon=True
        )
        processing_thread.start()

        logger.info(f"✅ Background thread started for {media_file_id}")

    def _process_background(
        self,
        interview_id: str,
        session_id: str,
        media_file_id: str,
        storage_uri: str
    ):
        """
        Background worker for video processing

        This runs in a separate thread and:
        1. Updates status to 'processing'
        2. Downloads from Azure Blob
        3. Processes video (face detection, emotions, gaze)
        4. Saves results to ai_analysis table
        5. Updates status to 'completed' or 'failed'
        """
        uow = None
        video_path = None

        try:
            import time
            start_time = time.time()

            logger.info("🎬 [Background] Video processing started")
            logger.info(f"   Media File: {media_file_id}")
            logger.info(f"   Interview: {interview_id}")
            logger.info(f"   Session: {session_id}")
            logger.info(f"   Storage URI: {storage_uri}")

            # Initialize database
            uow = UnitOfWork()
            repo = VideoRepository(uow)

            # Get media file details to retrieve blob_name
            media_file = repo.get_media_file_by_id(media_file_id)
            if not media_file:
                raise Exception(f"Media file not found: {media_file_id}")

            blob_name = media_file.get('blob_name')
            logger.info(f"📦 Blob name: {blob_name}")

            # Note: Not updating media_files.status to avoid conflict with audio-ai-service
            # Both services process the same media_file concurrently

            # STEP 1: Download video from storage_uri
            logger.info("📥 Downloading video from storage")
            video_path = self._download_video(storage_uri, media_file_id, interview_id, blob_name)

            if not video_path or not os.path.exists(video_path):
                raise Exception(f"Video download failed: {storage_uri}")

            logger.info(f"✅ Video downloaded to: {video_path}")

            # STEP 2: Run video analysis using existing VideoAnalyzer
            logger.info("🎥 Running video analysis")
            _ensure_models()  # Load YOLO models
            analyzer = _make_analyzer()

            # Run analysis (returns: {ok, report_path, video_path, summary})
            analysis_result = analyzer.analyze(
                src_video_path=video_path,
                user_id=interview_id,  # Use interview_id as user_id
                source_url=storage_uri
            )

            if not analysis_result.get("ok"):
                raise Exception("Video analysis failed")

            summary = analysis_result.get("summary", {})
            report_path = analysis_result.get("report_path")

            logger.info(f"✅ Video analysis completed")
            logger.info(f"   Performance score: {summary.get('performance', {}).get('score', 'N/A')}")
            logger.info(f"   Cheating probability: {summary.get('cheating_probability', 'N/A')}")

            # Load full report for detailed segments/events
            full_report = {}
            if report_path and os.path.exists(report_path):
                try:
                    with open(report_path, 'r') as f:
                        full_report = json.load(f)
                    logger.info(f"✅ Loaded full report with {len(full_report.get('segments', []))} segments")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load full report: {str(e)}")

            # STEP 3: Extract key metrics for database
            analysis_data = {
                # Core metrics
                "face_presence": summary.get("face_presence", 0.0),
                "time_to_first_face_sec": summary.get("time_to_first_face_sec", 0.0),
                "avg_attention_ema": summary.get("avg_attention_ema", 0.0),
                "avg_engagement": summary.get("avg_engagement", 0.0),
                "lighting_mean": summary.get("lighting_mean", 0.5),

                # Behavior metrics
                "look_away_ratio": summary.get("look_away_ratio", 0.0),
                "slouch_ratio": summary.get("slouch_ratio", 0.0),
                "hand_near_face_ratio": summary.get("hand_near_face_ratio", 0.0),
                "blink_ratio": summary.get("blink_ratio", 0.0),
                "nod_ratio": summary.get("nod_ratio", 0.0),

                # Integrity metrics
                "multi_person_ratio": summary.get("multi_person_ratio", 0.0),
                "prohibited_ratio": summary.get("prohibited_ratio", 0.0),
                "cheating_probability": summary.get("cheating_probability", 0.0),

                # Emotion analysis
                "emotion_top": summary.get("emotion_top", {}),
                "emotion_frames": summary.get("emotion_frames", 0),

                # Performance score
                "performance": summary.get("performance", {}),

                # Metadata
                "frames_total": summary.get("frames_total", 0),
                "frames_analyzed": summary.get("frames_analyzed", 0),
                "num_segments": summary.get("num_segments", 0),
                "report_path": analysis_result.get("report_path"),
                "processed_at": datetime.now(timezone.utc).isoformat(),

                # DETAILED SEGMENTS with timestamps (IMPORTANT for HR review!)
                "segments": full_report.get("segments", []),
                # Example segments:
                # [
                #   {"type": "multi_person", "start": 12.5, "end": 18.3},
                #   {"type": "prohibited_item", "start": 45.2, "end": 52.1},
                #   {"type": "look_away", "start": 30.0, "end": 35.5}
                # ]

                # Frame-level events (optional, for deep analysis)
                # "events": full_report.get("events", [])[:100]  # Limit to first 100 events to save space
            }

            # Add emotion ratios if present
            for key, value in summary.items():
                if key.startswith("emotion_") and key.endswith("_ratio"):
                    analysis_data[key] = value

            # Log important segments for debugging
            segments = full_report.get("segments", [])
            cheating_segments = [s for s in segments if s.get("type") in ["multi_person", "prohibited_item"]]
            if cheating_segments:
                logger.warning(f"⚠️ INTEGRITY ALERTS: {len(cheating_segments)} incidents detected:")
                for seg in cheating_segments[:5]:  # Log first 5
                    logger.warning(f"   - {seg.get('type')} from {seg.get('start'):.1f}s to {seg.get('end'):.1f}s")

            # Extract confidence score (0-10 scale to match audio-ai-service)
            performance = summary.get("performance", {})
            overall_score = float(performance.get("score", 0.0))  # Already 0-100 scale
            cheating_probability = float(summary.get("cheating_probability", 0.0))

            # Convert to 0-10 confidence score (10 = very confident, 0 = not confident)
            # Higher performance score and lower cheating = higher confidence
            confidence_score = (overall_score / 10.0) * (1.0 - cheating_probability)

            # Calculate processing time
            processing_time = int(time.time() - start_time)

            # STEP 4: Save results to database
            logger.info("💾 Saving analysis results to database")
            repo.save_video_analysis(
                interview_id=interview_id,
                session_id=session_id,
                analysis_data=analysis_data,
                confidence_score=confidence_score,
                processing_time=processing_time
            )

            # Note: Not updating media_files.status to avoid conflict with audio-ai-service
            logger.info("✅ [Background] Video processing completed successfully")

        except Exception as e:
            logger.error(f"❌ [Background] Video processing failed: {str(e)}", exc_info=True)
            # Note: Not updating media_files.status to avoid conflict with audio-ai-service

        finally:
            # Cleanup temp video file
            if video_path and os.path.exists(video_path):
                try:
                    # Only delete if it's in temp directory (not original local file)
                    if tempfile.gettempdir() in video_path:
                        os.remove(video_path)
                        logger.info(f"🗑️ Cleaned up temp video: {video_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp video: {str(e)}")

            # Cleanup database connection
            if uow:
                try:
                    uow.session.close()
                except Exception as e:
                    logger.error(f"❌ Error closing database connection: {str(e)}")
