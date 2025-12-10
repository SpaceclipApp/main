"""
Project repository for database operations
"""
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.project_model import ProjectModel
from models.media_project_model import MediaProjectModel


class ProjectRepository:
    """Repository for Project database operations"""
    
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
    
    # Media-Project associations
    
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


# Singleton instance
project_repository = ProjectRepository()
