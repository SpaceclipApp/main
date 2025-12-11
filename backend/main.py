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
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Upload directory: {settings.upload_dir}")
    logger.info(f"   Output directory: {settings.output_dir}")
    logger.info(f"   Frontend URL: {settings.frontend_url}")
    logger.info(f"   CORS allowed origins: {settings.allowed_origins if settings.allowed_origins else 'Not set (using frontend_url)'}")
    logger.info(f"   Ollama host: {settings.ollama_host}")
    logger.info(f"   Whisper model: {settings.whisper_model}")
    
    # Validate critical settings (should already be validated in config.py, but double-check)
    if not settings.secret_key:
        logger.error("   ❌ SECRET_KEY is required but not set")
        raise ValueError("SECRET_KEY is required but not set")
    
    if not settings.database_url:
        logger.error("   ❌ DATABASE_URL is required but not set")
        raise ValueError("DATABASE_URL is required but not set")
    
    if not settings.frontend_url:
        logger.error("   ❌ FRONTEND_URL is required but not set")
        raise ValueError("FRONTEND_URL is required but not set")
    
    # Validate ALLOWED_ORIGINS in production/staging
    if settings.environment in ("production", "staging"):
        if not settings.allowed_origins:
            logger.error("   ❌ ALLOWED_ORIGINS is required in production/staging but not set")
            raise ValueError(
                "ALLOWED_ORIGINS is required in production/staging. "
                "Set it as a comma-separated list, e.g., "
                "ALLOWED_ORIGINS=https://spaceclip.io,https://www.spaceclip.io"
            )
        logger.info(f"   ✅ CORS origins configured for {settings.environment}")
    
    logger.info("   ✅ Configuration validated")
    
    # Test database connection
    logger.info("   Testing database connection...")
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        logger.info("   ✅ Database connection successful")
        # Log database host (mask credentials)
        db_display = settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'
        logger.info(f"   Database: {db_display}")
    except Exception as e:
        logger.error(f"   ❌ Database connection failed: {e}")
        # Re-raise to prevent app from starting with broken DB
        raise
    
    if settings.redis_url:
        logger.info(f"   Redis URL: {settings.redis_url.split('@')[1] if '@' in settings.redis_url else 'configured'}")
    else:
        logger.info("   Redis: Not configured (using in-memory rate limiting)")
    
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
# Use allowed_origins from settings (validated in config.py)
# In production/staging, ALLOWED_ORIGINS env var is required
# In development, defaults to frontend_url if not set
cors_origins = settings.allowed_origins if settings.allowed_origins else [settings.frontend_url]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"   CORS origins: {cors_origins}")

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
    
    # Check database connection
    database_available = False
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            database_available = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Determine overall status
    status = "healthy" if database_available else "degraded"
    
    return {
        "status": status,
        "dependencies": {
            "database": database_available,
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

