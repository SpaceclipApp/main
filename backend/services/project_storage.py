"""
Project storage service for persistence
Uses PostgreSQL for metadata and disk for file storage
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import (
    ProjectState, MediaInfo, TranscriptionResult, HighlightAnalysis, 
    ClipResult, TranscriptSegment, Highlight, ProcessingStatus
)
from models.media_model import MediaModel
from models.transcription_model import TranscriptionModel, TranscriptSegmentModel
from models.highlight_model import HighlightModel
from models.clip_model import ClipModel
from repositories.project_repository import (
    media_repository,
    transcription_repository,
    highlight_repository,
    clip_repository,
)

logger = logging.getLogger(__name__)

# Storage directory for files (still needed for media and clip files)
PROJECTS_DIR = settings.upload_dir / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


class ProjectStorage:
    """Handles project persistence to database and disk"""
    
    def __init__(self):
        self.projects_dir = PROJECTS_DIR
        self.media_repo = media_repository
        self.transcription_repo = transcription_repository
        self.highlight_repo = highlight_repository
        self.clip_repo = clip_repository
    
    # -------------------------------------------------------------------------
    # Conversion helpers: ORM models <-> Pydantic models
    # -------------------------------------------------------------------------
    
    def _media_model_to_pydantic(self, model: MediaModel) -> MediaInfo:
        """Convert SQLAlchemy MediaModel to Pydantic MediaInfo"""
        return MediaInfo(
            id=str(model.id),
            filename=model.filename,
            original_filename=model.original_filename,
            media_type=model.media_type,
            source_type=model.source_type,
            source_url=model.source_url,
            duration=model.duration,
            file_path=model.file_path,
            thumbnail_path=model.thumbnail_path,
            created_at=model.created_at,
        )
    
    def _transcription_model_to_pydantic(self, model: TranscriptionModel) -> TranscriptionResult:
        """Convert SQLAlchemy TranscriptionModel to Pydantic TranscriptionResult"""
        segments = [
            TranscriptSegment(
                id=seg.segment_index,
                start=seg.start_time,
                end=seg.end_time,
                text=seg.text,
                speaker=seg.speaker,
                confidence=seg.confidence,
            )
            for seg in model.segments
        ]
        return TranscriptionResult(
            media_id=str(model.media_id),
            language=model.language,
            segments=segments,
            full_text=model.full_text,
        )
    
    def _highlights_to_pydantic(self, models: list[HighlightModel], media_id: str) -> HighlightAnalysis:
        """Convert SQLAlchemy HighlightModels to Pydantic HighlightAnalysis"""
        highlights = [
            Highlight(
                id=h.highlight_id,
                start=h.start_time,
                end=h.end_time,
                title=h.title,
                description=h.description,
                score=h.score,
                tags=h.tags or [],
                transcript_segment_ids=h.transcript_segment_ids or [],
            )
            for h in models
        ]
        return HighlightAnalysis(
            media_id=media_id,
            highlights=highlights,
            analyzed_at=models[0].created_at if models else datetime.utcnow(),
        )
    
    def _clip_model_to_pydantic(self, model: ClipModel) -> ClipResult:
        """Convert SQLAlchemy ClipModel to Pydantic ClipResult"""
        return ClipResult(
            id=str(model.id),
            media_id=str(model.media_id),
            platform=model.platform,
            file_path=model.file_path,
            duration=model.duration,
            width=model.width,
            height=model.height,
            has_captions=model.has_captions,
            created_at=model.created_at,
        )
    
    # -------------------------------------------------------------------------
    # Save operations
    # -------------------------------------------------------------------------
    
    async def save_project(self, db: AsyncSession, media_id: str, state: ProjectState, project_id: Optional[str] = None) -> None:
        """Save project state to database"""
        try:
            media_uuid = UUID(media_id)
            project_uuid = UUID(project_id) if project_id else None
            
            # Check if media exists
            existing_media = await self.media_repo.get_by_id(db, media_uuid)
            
            if existing_media:
                # Update existing media
                existing_media.status = state.status.value if hasattr(state.status, 'value') else str(state.status)
                existing_media.progress = state.progress or 0
                existing_media.error = state.error
                if state.media:
                    existing_media.duration = state.media.duration
                    existing_media.thumbnail_path = state.media.thumbnail_path
                # Update project_id if provided and not already set
                if project_uuid and not existing_media.project_id:
                    existing_media.project_id = project_uuid
                await self.media_repo.update(db, existing_media)
            elif state.media:
                # Create new media entry with project_id
                media_model = MediaModel(
                    id=media_uuid,
                    project_id=project_uuid,  # Link to user's project
                    filename=state.media.filename,
                    original_filename=state.media.original_filename,
                    file_path=state.media.file_path,
                    thumbnail_path=state.media.thumbnail_path,
                    media_type=state.media.media_type.value if hasattr(state.media.media_type, 'value') else state.media.media_type,
                    source_type=state.media.source_type.value if hasattr(state.media.source_type, 'value') else state.media.source_type,
                    source_url=state.media.source_url,
                    duration=state.media.duration,
                    status=state.status.value if hasattr(state.status, 'value') else str(state.status),
                    progress=state.progress or 0,
                    error=state.error,
                )
                await self.media_repo.create(db, media_model)
            
            # Save transcription if present
            if state.transcription:
                await self._save_transcription(db, media_uuid, state.transcription)
            
            # Save highlights if present
            if state.highlights:
                await self._save_highlights(db, media_uuid, state.highlights)
            
            # Save clips if present
            if state.clips:
                await self._save_clips(db, media_uuid, state.clips)
            
            logger.info(f"Saved project {media_id}")
        except Exception as e:
            logger.error(f"Failed to save project {media_id}: {e}")
            raise
    
    async def _save_transcription(
        self, 
        db: AsyncSession, 
        media_id: UUID, 
        transcription: TranscriptionResult
    ) -> None:
        """Save or update transcription"""
        # Delete existing transcription if any
        await self.transcription_repo.delete_by_media_id(db, media_id)
        
        # Create new transcription
        transcription_model = TranscriptionModel(
            media_id=media_id,
            language=transcription.language,
            full_text=transcription.full_text,
        )
        
        segments = [
            TranscriptSegmentModel(
                transcription_id=None,  # Will be set by create_with_segments
                segment_index=seg.id,
                start_time=seg.start,
                end_time=seg.end,
                text=seg.text,
                speaker=seg.speaker,
                confidence=seg.confidence,
            )
            for seg in transcription.segments
        ]
        
        await self.transcription_repo.create_with_segments(db, transcription_model, segments)
    
    async def _save_highlights(
        self, 
        db: AsyncSession, 
        media_id: UUID, 
        highlight_analysis: HighlightAnalysis
    ) -> None:
        """Save or update highlights"""
        # Delete existing highlights
        await self.highlight_repo.delete_by_media_id(db, media_id)
        
        # Create new highlights
        highlight_models = [
            HighlightModel(
                media_id=media_id,
                highlight_id=h.id,
                start_time=h.start,
                end_time=h.end,
                title=h.title,
                description=h.description,
                score=h.score,
                tags=h.tags,
                transcript_segment_ids=h.transcript_segment_ids,
            )
            for h in highlight_analysis.highlights
        ]
        
        if highlight_models:
            await self.highlight_repo.create_many(db, highlight_models)
    
    async def _save_clips(
        self, 
        db: AsyncSession, 
        media_id: UUID, 
        clips: list[ClipResult]
    ) -> None:
        """Save clips (additive - doesn't delete existing)"""
        for clip in clips:
            # Check if clip already exists (by ID)
            try:
                clip_uuid = UUID(clip.id)
                existing_clips = await self.clip_repo.get_by_media_id(db, media_id)
                existing_ids = {str(c.id) for c in existing_clips}
                
                if clip.id not in existing_ids:
                    clip_model = ClipModel(
                        id=clip_uuid,
                        media_id=media_id,
                        platform=clip.platform.value if hasattr(clip.platform, 'value') else clip.platform,
                        file_path=clip.file_path,
                        duration=clip.duration,
                        width=clip.width,
                        height=clip.height,
                        has_captions=clip.has_captions,
                    )
                    await self.clip_repo.create(db, clip_model)
            except Exception as e:
                logger.error(f"Failed to save clip {clip.id}: {e}")
    
    # -------------------------------------------------------------------------
    # Load operations
    # -------------------------------------------------------------------------
    
    async def load_project(self, db: AsyncSession, media_id: str, user_id: Optional[str] = None) -> Optional[ProjectState]:
        """Load project state from database with optional user ownership check."""
        try:
            media_uuid = UUID(media_id)

            # Load media with all relations
            media_model = await self.media_repo.get_by_id_with_relations(db, media_uuid)
            if not media_model:
                return None

            # Resolve owning user + project from the media's project_id
            resolved_user_id: Optional[str] = None
            resolved_project_id: Optional[str] = None

            if media_model.project_id:
                resolved_project_id = str(media_model.project_id)
                from repositories.project_repository import project_repository
                project = await project_repository.get_by_id(db, media_model.project_id)
                if project:
                    resolved_user_id = str(project.user_id)

            # Ownership check: if caller provided user_id, enforce it
            if user_id and resolved_user_id and resolved_user_id != user_id:
                # Media belongs to a different user
                return None

            # Convert to Pydantic models
            media = self._media_model_to_pydantic(media_model)

            transcription = None
            if media_model.transcription:
                transcription = self._transcription_model_to_pydantic(media_model.transcription)

            highlights = None
            if media_model.highlights:
                highlights = self._highlights_to_pydantic(media_model.highlights, media_id)

            clips = [self._clip_model_to_pydantic(c) for c in media_model.clips]

            # Map status string to enum
            try:
                status = ProcessingStatus(media_model.status)
            except ValueError:
                status = ProcessingStatus.PENDING

            return ProjectState(
                user_id=resolved_user_id,
                project_id=resolved_project_id,
                media=media,
                status=status,
                progress=media_model.progress,
                error=media_model.error,
                transcription=transcription,
                highlights=highlights,
                clips=clips,
            )
        except Exception as e:
            logger.error(f"Failed to load project {media_id}: {e}")
            return None
    
    async def list_projects(self, db: AsyncSession, user_id: Optional[str] = None, include_archived: bool = False) -> list[dict]:
        """List saved media for current user only"""
        try:
            if not user_id:
                # No user - return empty list to prevent data leakage
                return []

            # Get user's projects first
            from repositories.project_repository import project_repository
            user_projects = await project_repository.get_by_user_id(db, UUID(user_id))
            project_ids = [p.id for p in user_projects]

            # Get media belonging to user's projects ONLY
            media_list = []
            for project_id in project_ids:
                project_media = await self.media_repo.get_by_project_id(db, project_id)
                media_list.extend(project_media)
            
            projects = []
            seen_ids = set()  # Prevent duplicates
            for media in media_list:
                if str(media.id) in seen_ids:
                    continue
                seen_ids.add(str(media.id))
                
                # Skip archived media unless explicitly requested
                if not include_archived and media.status == "archived":
                    continue

                
                # Get highlight count
                highlights = await self.highlight_repo.get_by_media_id(db, media.id)
                clips = await self.clip_repo.get_by_media_id(db, media.id)
                
                projects.append({
                    "media_id": str(media.id),
                    "title": media.original_filename or media.filename or "Untitled",
                    "media_type": media.media_type,
                    "duration": media.duration,
                    "status": media.status,
                    "saved_at": media.updated_at.isoformat() if media.updated_at else None,
                    "clips_count": len(clips),
                    "highlights_count": len(highlights),
                })
            
            # Sort by saved_at descending
            projects.sort(key=lambda x: x["saved_at"] or "", reverse=True)
            
            return projects
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # Delete operations
    # -------------------------------------------------------------------------
    
    async def delete_project_async(self, db: AsyncSession, media_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a saved project and its associated files (async version)"""
        try:
            media_uuid = UUID(media_id)
            
            # Get media to find file paths
            media_model = await self.media_repo.get_by_id(db, media_uuid)
            
            if media_model:
                # Verify ownership if user_id provided
                if user_id and media_model.project_id:
                    from repositories.project_repository import project_repository
                    project = await project_repository.get_by_id(db, media_model.project_id)
                    if project and str(project.user_id) != user_id:
                        logger.warning(f"User {user_id} attempted to delete media {media_id} owned by another user")
                        return False
                
                # Get clips to delete their files
                clips = await self.clip_repo.get_by_media_id(db, media_uuid)
                
                # Delete clip files
                for clip in clips:
                    clip_path = Path(clip.file_path)
                    if clip_path.exists():
                        clip_path.unlink()
                        logger.info(f"Deleted clip file: {clip_path}")
                
                # Delete media file
                media_path = Path(media_model.file_path)
                if media_path.exists():
                    media_path.unlink()
                    logger.info(f"Deleted media file: {media_path}")
                
                # Delete from database (cascades to related tables)
                await self.media_repo.delete(db, media_uuid)
                logger.info(f"Deleted project {media_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to delete project {media_id}: {e}")
            return False
    
    async def archive_media(self, db: AsyncSession, media_id: str, user_id: Optional[str] = None) -> bool:
        """Archive a media item (soft delete)"""
        try:
            media_uuid = UUID(media_id)
            media_model = await self.media_repo.get_by_id(db, media_uuid)
            
            if not media_model:
                return False
            
            # Verify ownership if user_id provided
            if user_id and media_model.project_id:
                from repositories.project_repository import project_repository
                project = await project_repository.get_by_id(db, media_model.project_id)
                if project and str(project.user_id) != user_id:
                    return False
            
            # Update status to archived
            await self.media_repo.update_status(db, media_uuid, "archived")
            logger.info(f"Archived media {media_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive media {media_id}: {e}")
            return False
    
    async def unarchive_media(self, db: AsyncSession, media_id: str, user_id: Optional[str] = None) -> bool:
        """Unarchive a media item"""
        try:
            media_uuid = UUID(media_id)
            media_model = await self.media_repo.get_by_id(db, media_uuid)
            
            if not media_model:
                return False
            
            # Verify ownership if user_id provided
            if user_id and media_model.project_id:
                from repositories.project_repository import project_repository
                project = await project_repository.get_by_id(db, media_model.project_id)
                if project and str(project.user_id) != user_id:
                    return False
            
            # Update status to complete (or pending if never processed)
            new_status = "complete" if media_model.progress >= 1.0 else "pending"
            await self.media_repo.update_status(db, media_uuid, new_status)
            logger.info(f"Unarchived media {media_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unarchive media {media_id}: {e}")
            return False
    
    def delete_project(self, media_id: str) -> bool:
        """
        Synchronous version of delete_project - deletes files only.
        
        Note: This is a compatibility method for synchronous contexts.
        It only deletes files from disk, not database records.
        Use delete_project_async for full deletion.
        """
        deleted = False
        
        # Delete associated media files
        for ext in ['m4a', 'mp3', 'wav', 'mp4', 'webm', 'ogg']:
            media_path = settings.upload_dir / f"{media_id}.{ext}"
            if media_path.exists():
                media_path.unlink()
                logger.info(f"Deleted media file: {media_path}")
                deleted = True
        
        # Delete generated clips (all files starting with media_id prefix)
        for clip_file in settings.output_dir.glob(f"*"):
            if str(clip_file.name).startswith(media_id[:8]):
                clip_file.unlink()
                logger.info(f"Deleted clip file: {clip_file}")
                deleted = True
        
        return deleted
    
    async def clear_project_clips(self, db: AsyncSession, media_id: str) -> bool:
        """Clear all generated clips for a project"""
        try:
            media_uuid = UUID(media_id)
            
            # Get clips to delete their files
            clips = await self.clip_repo.get_by_media_id(db, media_uuid)
            
            for clip in clips:
                clip_path = Path(clip.file_path)
                if clip_path.exists():
                    clip_path.unlink()
                    logger.info(f"Deleted clip file: {clip_path}")
            
            # Delete from database
            await self.clip_repo.delete_by_media_id(db, media_uuid)
            
            logger.info(f"Cleared clips for project {media_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear clips for {media_id}: {e}")
            return False
    
    async def project_exists(self, db: AsyncSession, media_id: str) -> bool:
        """Check if a project exists"""
        try:
            media_uuid = UUID(media_id)
            return await self.media_repo.exists(db, media_uuid)
        except Exception:
            return False


# Singleton instance
project_storage = ProjectStorage()
