"""
User repository for database operations
"""
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_model import UserModel
from models.password_model import PasswordHashModel


class UserRepository:
    """Repository for User database operations"""
    
    async def get_by_email(self, db: AsyncSession, email: str) -> UserModel | None:
        """Get user by email address"""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> UserModel | None:
        """Get user by ID"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_wallet_address(self, db: AsyncSession, wallet_address: str) -> UserModel | None:
        """Get user by wallet address"""
        stmt = select(UserModel).where(UserModel.wallet_address == wallet_address)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, db: AsyncSession, user: UserModel) -> UserModel:
        """Create a new user"""
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def update(self, db: AsyncSession, user: UserModel) -> UserModel:
        """Update an existing user"""
        await db.commit()
        await db.refresh(user)
        return user
    
    async def delete(self, db: AsyncSession, user_id: UUID) -> bool:
        """Delete a user by ID"""
        stmt = delete(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
    
    async def email_exists(self, db: AsyncSession, email: str) -> bool:
        """Check if email is already registered"""
        stmt = select(UserModel.id).where(UserModel.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def get_password_hash(self, db: AsyncSession, user_id: UUID) -> PasswordHashModel | None:
        """Get password hash for user"""
        stmt = select(PasswordHashModel).where(PasswordHashModel.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_password_hash(self, db: AsyncSession, password_hash: PasswordHashModel) -> PasswordHashModel:
        """Create password hash for user"""
        db.add(password_hash)
        await db.commit()
        await db.refresh(password_hash)
        return password_hash
    
    async def update_password_hash(self, db: AsyncSession, user_id: UUID, new_hash: str) -> bool:
        """Update password hash for user"""
        stmt = (
            update(PasswordHashModel)
            .where(PasswordHashModel.user_id == user_id)
            .values(password_hash=new_hash)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0


# Singleton instance
user_repository = UserRepository()

