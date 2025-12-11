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

# Create async engine with connection pool settings
async_engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL query logging in development
    future=True,
    pool_size=5,  # Number of connections to maintain in the pool
    max_overflow=10,  # Maximum number of connections to create beyond pool_size
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection
    pool_recycle=1800,  # Seconds before recreating a connection (30 minutes)
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

