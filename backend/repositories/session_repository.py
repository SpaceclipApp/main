"""
Session repository for database operations
"""
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.session_model import SessionModel


class SessionRepository:
    """Repository for Session database operations"""
    
    async def get_by_token(self, db: AsyncSession, token: str) -> SessionModel | None:
        """Get session by token"""
        stmt = select(SessionModel).where(SessionModel.token == token)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, db: AsyncSession, session_id: UUID) -> SessionModel | None:
        """Get session by ID"""
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, db: AsyncSession, user_id: UUID) -> list[SessionModel]:
        """Get all sessions for a user"""
        stmt = select(SessionModel).where(SessionModel.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, session: SessionModel) -> SessionModel:
        """Create a new session"""
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    async def update(self, db: AsyncSession, session: SessionModel) -> SessionModel:
        """Update an existing session"""
        await db.commit()
        await db.refresh(session)
        return session
    
    async def update_last_active(self, db: AsyncSession, token: str) -> bool:
        """Update last_active_at for a session"""
        stmt = (
            update(SessionModel)
            .where(SessionModel.token == token)
            .values(last_active_at=datetime.utcnow())
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def extend_expiration(self, db: AsyncSession, token: str, new_expires_at: datetime) -> bool:
        """Extend session expiration"""
        stmt = (
            update(SessionModel)
            .where(SessionModel.token == token)
            .values(expires_at=new_expires_at, last_active_at=datetime.utcnow())
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete(self, db: AsyncSession, session_id: UUID) -> bool:
        """Delete a session by ID"""
        stmt = delete(SessionModel).where(SessionModel.id == session_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete_by_token(self, db: AsyncSession, token: str) -> bool:
        """Delete a session by token"""
        stmt = delete(SessionModel).where(SessionModel.token == token)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def delete_expired(self, db: AsyncSession) -> int:
        """Delete all expired sessions"""
        stmt = delete(SessionModel).where(SessionModel.expires_at < datetime.utcnow())
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount
    
    async def delete_all_for_user(self, db: AsyncSession, user_id: UUID) -> int:
        """Delete all sessions for a user"""
        stmt = delete(SessionModel).where(SessionModel.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


# Singleton instance
session_repository = SessionRepository()

