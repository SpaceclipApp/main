"""
Project repository for database operations
"""
from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.project_model import ProjectModel
from models.media_project_model import MediaProjectModel
from models.media_model import MediaModel
from models.transcription_model import TranscriptionModel, TranscriptSegmentModel
from models.highlight_model import HighlightModel
from models.clip_model import ClipModel


class ProjectRepository:
    """Repository for Project database operations"""
    
    # -------------------------------------------------------------------------
    # Project CRUD
    # -------------------------------------------------------------------------
    
    async def get_by_id(self, db: AsyncSession, project_id: UUID) -> ProjectModel | None:
        """Get project by ID"""
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, db: AsyncSession, user_id: UUID) -> list[ProjectModel]:
        """Get all projects for a user"""
        stmt = select(ProjectModel).where(ProjectModel.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_by_user_id(self, db: AsyncSession, user_id: UUID) -> list[ProjectModel]:
        """Get all active projects for a user"""
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.user_id == user_id)
            .where(ProjectModel.status == "active")
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, project: ProjectModel) -> ProjectModel:
        """Create a new project"""
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project
    
    async def update(self, db: AsyncSession, project: ProjectModel) -> ProjectModel:
        """Update an existing project"""
        await db.commit()
        await db.refresh(project)
        return project
    
    async def update_status(self, db: AsyncSession, project_id: UUID, status: str) -> bool:
        """Update project status"""
        stmt = (
            update(ProjectModel)
            .where(ProjectModel.id == project_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete(self, db: AsyncSession, project_id: UUID) -> bool:
        """Delete a project by ID"""
        stmt = delete(ProjectModel).where(ProjectModel.id == project_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete_by_user(self, db: AsyncSession, user_id: UUID, project_id: UUID) -> bool:
        """Delete a project if owned by user"""
        stmt = (
            delete(ProjectModel)
            .where(ProjectModel.id == project_id)
            .where(ProjectModel.user_id == user_id)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    # -------------------------------------------------------------------------
    # Media-Project associations (legacy)
    # -------------------------------------------------------------------------
    
    async def add_media(self, db: AsyncSession, media_project: MediaProjectModel) -> MediaProjectModel:
        """Add media to a project"""
        db.add(media_project)
        await db.commit()
        await db.refresh(media_project)
        return media_project
    
    async def get_media_by_project(self, db: AsyncSession, project_id: UUID) -> list[MediaProjectModel]:
        """Get all media for a project"""
        stmt = select(MediaProjectModel).where(MediaProjectModel.project_id == project_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def remove_media(self, db: AsyncSession, media_id: UUID) -> bool:
        """Remove media from project"""
        stmt = delete(MediaProjectModel).where(MediaProjectModel.media_id == media_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def clear_project_media(self, db: AsyncSession, project_id: UUID) -> int:
        """Clear all media from a project"""
        stmt = delete(MediaProjectModel).where(MediaProjectModel.project_id == project_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


class MediaRepository:
    """Repository for Media database operations"""
    
    async def get_by_id(self, db: AsyncSession, media_id: UUID) -> MediaModel | None:
        """Get media by ID"""
        stmt = select(MediaModel).where(MediaModel.id == media_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id_with_relations(self, db: AsyncSession, media_id: UUID) -> MediaModel | None:
        """Get media by ID with all related data loaded"""
        stmt = (
            select(MediaModel)
            .where(MediaModel.id == media_id)
            .options(
                selectinload(MediaModel.transcription).selectinload(TranscriptionModel.segments),
                selectinload(MediaModel.highlights),
                selectinload(MediaModel.clips),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_project_id(self, db: AsyncSession, project_id: UUID) -> list[MediaModel]:
        """Get all media for a project"""
        stmt = select(MediaModel).where(MediaModel.project_id == project_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def list_all(self, db: AsyncSession, limit: int = 100) -> list[MediaModel]:
        """List all media (for listing projects)"""
        stmt = select(MediaModel).order_by(MediaModel.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, media: MediaModel) -> MediaModel:
        """Create a new media entry"""
        db.add(media)
        await db.commit()
        await db.refresh(media)
        return media
    
    async def update(self, db: AsyncSession, media: MediaModel) -> MediaModel:
        """Update an existing media entry"""
        await db.commit()
        await db.refresh(media)
        return media
    
    async def update_status(
        self, 
        db: AsyncSession, 
        media_id: UUID, 
        status: str, 
        progress: float = None,
        error: str = None
    ) -> bool:
        """Update media processing status"""
        values = {"status": status, "updated_at": datetime.utcnow()}
        if progress is not None:
            values["progress"] = progress
        if error is not None:
            values["error"] = error
        
        stmt = (
            update(MediaModel)
            .where(MediaModel.id == media_id)
            .values(**values)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete(self, db: AsyncSession, media_id: UUID) -> bool:
        """Delete a media entry by ID (cascades to related data)"""
        stmt = delete(MediaModel).where(MediaModel.id == media_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def exists(self, db: AsyncSession, media_id: UUID) -> bool:
        """Check if media exists"""
        stmt = select(MediaModel.id).where(MediaModel.id == media_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None


class TranscriptionRepository:
    """Repository for Transcription database operations"""
    
    async def get_by_media_id(self, db: AsyncSession, media_id: UUID) -> TranscriptionModel | None:
        """Get transcription for a media item"""
        stmt = (
            select(TranscriptionModel)
            .where(TranscriptionModel.media_id == media_id)
            .options(selectinload(TranscriptionModel.segments))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, db: AsyncSession, transcription: TranscriptionModel) -> TranscriptionModel:
        """Create a new transcription"""
        db.add(transcription)
        await db.commit()
        await db.refresh(transcription)
        return transcription
    
    async def create_with_segments(
        self, 
        db: AsyncSession, 
        transcription: TranscriptionModel,
        segments: list[TranscriptSegmentModel]
    ) -> TranscriptionModel:
        """Create transcription with all segments"""
        db.add(transcription)
        await db.flush()  # Get transcription ID
        
        for segment in segments:
            segment.transcription_id = transcription.id
            db.add(segment)
        
        await db.commit()
        await db.refresh(transcription)
        return transcription
    
    async def delete_by_media_id(self, db: AsyncSession, media_id: UUID) -> bool:
        """Delete transcription for a media item"""
        stmt = delete(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0


class HighlightRepository:
    """Repository for Highlight database operations"""
    
    async def get_by_media_id(self, db: AsyncSession, media_id: UUID) -> list[HighlightModel]:
        """Get all highlights for a media item"""
        stmt = (
            select(HighlightModel)
            .where(HighlightModel.media_id == media_id)
            .order_by(HighlightModel.start_time)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, highlight: HighlightModel) -> HighlightModel:
        """Create a new highlight"""
        db.add(highlight)
        await db.commit()
        await db.refresh(highlight)
        return highlight
    
    async def create_many(self, db: AsyncSession, highlights: list[HighlightModel]) -> list[HighlightModel]:
        """Create multiple highlights"""
        for highlight in highlights:
            db.add(highlight)
        await db.commit()
        for highlight in highlights:
            await db.refresh(highlight)
        return highlights
    
    async def delete_by_media_id(self, db: AsyncSession, media_id: UUID) -> int:
        """Delete all highlights for a media item"""
        stmt = delete(HighlightModel).where(HighlightModel.media_id == media_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


class ClipRepository:
    """Repository for Clip database operations"""
    
    async def get_by_media_id(self, db: AsyncSession, media_id: UUID) -> list[ClipModel]:
        """Get all clips for a media item"""
        stmt = (
            select(ClipModel)
            .where(ClipModel.media_id == media_id)
            .order_by(ClipModel.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, clip: ClipModel) -> ClipModel:
        """Create a new clip"""
        db.add(clip)
        await db.commit()
        await db.refresh(clip)
        return clip
    
    async def delete(self, db: AsyncSession, clip_id: UUID) -> bool:
        """Delete a clip by ID"""
        stmt = delete(ClipModel).where(ClipModel.id == clip_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete_by_media_id(self, db: AsyncSession, media_id: UUID) -> int:
        """Delete all clips for a media item"""
        stmt = delete(ClipModel).where(ClipModel.media_id == media_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


# Singleton instances
project_repository = ProjectRepository()
media_repository = MediaRepository()
transcription_repository = TranscriptionRepository()
highlight_repository = HighlightRepository()
clip_repository = ClipRepository()
