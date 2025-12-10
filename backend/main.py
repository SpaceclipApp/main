"""
SpaceClip Backend - FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from api import router
from api.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 SpaceClip Backend starting up...")
    logger.info(f"   Upload directory: {settings.upload_dir}")
    logger.info(f"   Output directory: {settings.output_dir}")
    logger.info(f"   Ollama host: {settings.ollama_host}")
    logger.info(f"   Whisper model: {settings.whisper_model}")
    
    yield
    
    logger.info("SpaceClip Backend shutting down...")


app = FastAPI(
    title="SpaceClip API",
    description="Transform podcasts, videos, and X Spaces into viral clips",
    version="1.0.0",
    lifespan=lifespan,
)

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
app.include_router(auth_router, prefix="/api")


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

