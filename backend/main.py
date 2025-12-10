"""
SpaceClip Backend - FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from api import router
from api import auth_routes
from models.database import get_db_session, async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def db_session_dependency() -> AsyncSession:
    """
    FastAPI dependency to get a database session.
    
    Usage in routes:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(db_session_dependency)):
            # Use db session here
            pass
    """
    async for session in get_db_session():
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 SpaceClip Backend starting up...")
    logger.info(f"   Upload directory: {settings.upload_dir}")
    logger.info(f"   Output directory: {settings.output_dir}")
    logger.info(f"   Ollama host: {settings.ollama_host}")
    logger.info(f"   Whisper model: {settings.whisper_model}")
    
    # Test database connection
    logger.info("   Testing database connection...")
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        logger.info("   ✅ Database connection successful")
        logger.info(f"   Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    except Exception as e:
        logger.error(f"   ❌ Database connection failed: {e}")
        # Re-raise to prevent app from starting with broken DB
        raise
    
    yield
    
    logger.info("SpaceClip Backend shutting down...")
    # Close database engine
    await async_engine.dispose()
    logger.info("   Database connections closed")


app = FastAPI(
    title="SpaceClip API",
    description="Transform podcasts, videos, and X Spaces into viral clips",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Share limiter instance with auth routes
auth_routes.limiter = limiter

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for outputs
app.mount("/outputs", StaticFiles(directory=str(settings.output_dir)), name="outputs")
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# API routes
app.include_router(router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "SpaceClip API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    import shutil
    
    # Check FFmpeg
    ffmpeg_available = shutil.which("ffmpeg") is not None
    
    # Check Ollama
    ollama_available = False
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_host}/api/tags")
            ollama_available = response.status_code == 200
    except Exception:
        pass
    
    return {
        "status": "healthy",
        "dependencies": {
            "ffmpeg": ffmpeg_available,
            "ollama": ollama_available,
            "whisper": True,  # Will fail on first use if not working
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

