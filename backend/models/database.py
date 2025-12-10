"""
Database configuration and session management for SQLAlchemy 2.0 async ORM
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

from config import settings

# Declarative base for models
Base = declarative_base()

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL query logging in development
    future=True,
)

# Create async session maker
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get a database session.
    
    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            # Use db session here
            pass
    """
    async with async_session_maker() as session:
        yield session
