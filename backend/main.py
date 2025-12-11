"""
SpaceClip Backend - FastAPI Application
"""
import json
import logging
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from api import router
from api import auth_routes
from models.database import get_db_session, async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from logging_context import request_id_var, user_id_var


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent sensitive data from being logged"""
    
    SENSITIVE_FIELDS = {
        'password', 'password_hash', 'token', 'secret', 'secret_key',
        'authorization', 'bearer', 'api_key', 'apikey', 'access_token',
        'refresh_token', 'session_token', 'auth_token'
    }
    
    def filter(self, record):
        """Remove sensitive fields from log records"""
        # Check message
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            record.msg = self._sanitize_dict(record.msg)
        elif hasattr(record, 'msg') and isinstance(record.msg, str):
            # Try to parse as JSON and sanitize
            try:
                data = json.loads(record.msg)
                if isinstance(data, dict):
                    record.msg = json.dumps(self._sanitize_dict(data))
            except (json.JSONDecodeError, TypeError):
                # Not JSON, check for sensitive patterns in string
                record.msg = self._sanitize_string(record.msg)
        
        # Check args
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, dict):
                    sanitized_args.append(self._sanitize_dict(arg))
                elif isinstance(arg, str):
                    sanitized_args.append(self._sanitize_string(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return True
    
    def _sanitize_dict(self, data: dict) -> dict:
        """Remove sensitive fields from dictionary"""
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            # Check if key contains sensitive field name
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, str) and any(sensitive in value.lower() for sensitive in self.SENSITIVE_FIELDS):
                # Check if value contains sensitive data
                sanitized[key] = self._sanitize_string(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize sensitive patterns in string"""
        import re
        # Replace common patterns like "password=xxx" or "token: xxx"
        patterns = [
            (r'(?i)(password|token|secret|key)\s*[=:]\s*["\']?[^"\'\s]+["\']?', r'\1=***REDACTED***'),
            (r'(?i)bearer\s+[\w\-]+', 'Bearer ***REDACTED***'),
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
        
        # Add route if available (from record)
        if hasattr(record, 'route'):
            log_data["route"] = record.route
        elif hasattr(record, 'path'):
            log_data["route"] = record.path
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                          'request_id', 'user_id', 'route', 'path'):
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or get request ID from header
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Set in context
        request_id_var.set(request_id)
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests with route and user information"""
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID from context
        request_id = request_id_var.get()
        
        # Extract route information
        route = f"{request.method} {request.url.path}"
        
        # Try to get user_id from request state (set by auth dependencies)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            user_id_var.set(str(user_id))
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                "route": route,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Process request
        start_time = datetime.utcnow()
        status_code = 500  # Default to 500 in case of exception
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            logger.exception(
                "Request failed",
                extra={
                    "route": route,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise
        finally:
            # Log request completion
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                "Request completed",
                extra={
                    "route": route,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
        
        return response


def setup_logging():
    """Configure logging based on environment"""
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler()
    
    # Use JSON formatter in production/staging, simple formatter in development
    if settings.environment in ("production", "staging"):
        formatter = JSONFormatter()
    else:
        # Development formatter with request ID and user ID support
        class DevFormatter(logging.Formatter):
            def format(self, record):
                request_id = request_id_var.get()
                if request_id:
                    record.request_id = request_id
                else:
                    record.request_id = "N/A"
                
                user_id = user_id_var.get()
                if user_id:
                    record.user_id = f" [user:{user_id[:8]}...]"
                else:
                    record.user_id = ""
                
                return super().format(record)
        
        formatter = DevFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s]%(user_id)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    
    # Add sensitive data filter
    handler.addFilter(SensitiveDataFilter())
    
    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    
    # Set level for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return root_logger


# Setup logging
logger = setup_logging()


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

# Add request ID middleware (must be first)
app.add_middleware(RequestIDMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

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

