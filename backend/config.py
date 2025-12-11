from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from pathlib import Path
from typing import Optional, Literal


class Settings(BaseSettings):
    # Security
    secret_key: str = Field(..., description="Secret key for session signing/JWT (required)")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    
    # Database
    database_url: str = Field(..., description="PostgreSQL database URL (required)")
    
    # Redis (optional, for rate limiting/caching)
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis URL for rate limiting and caching (optional)"
    )
    
    # Frontend
    frontend_url: str = Field(..., description="Frontend URL for CORS and redirects (required)")
    
    # Ollama
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama API host URL"
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model name"
    )
    
    # Whisper
    whisper_model: str = Field(
        default="base",
        description="Whisper model name"
    )
    
    # Storage
    upload_dir: Path = Field(
        default=Path("./uploads"),
        description="Directory for uploaded files"
    )
    output_dir: Path = Field(
        default=Path("./outputs"),
        description="Directory for generated output files"
    )
    
    # Server
    host: str = Field(
        default="0.0.0.0",
        description="Server host to bind to"
    )
    port: int = Field(
        default=8000,
        description="Server port"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Public API URL (for generating absolute URLs to backend resources)
    # If not set, will be derived from frontend_url or host/port
    public_api_url: Optional[str] = Field(
        default=None,
        description="Public API URL for generating absolute URLs (e.g., https://api.spaceclip.io)"
    )
    
    def get_api_base_url(self) -> str:
        """Get the base URL for the API (for generating absolute URLs)"""
        if self.public_api_url:
            return self.public_api_url.rstrip("/")
        
        # Derive from frontend_url if it's a full URL
        if self.frontend_url.startswith("http"):
            # Try to derive API URL from frontend URL
            # e.g., http://localhost:3000 -> http://localhost:8000
            # or https://spaceclip.io -> https://api.spaceclip.io
            if "localhost" in self.frontend_url or "127.0.0.1" in self.frontend_url:
                # Development: use same host, different port
                base = self.frontend_url.rsplit(":", 1)[0] if ":" in self.frontend_url else self.frontend_url
                return f"{base}:{self.port}"
            else:
                # Production: try api subdomain
                from urllib.parse import urlparse
                parsed = urlparse(self.frontend_url)
                if parsed.netloc:
                    # Replace or prepend api subdomain
                    netloc = parsed.netloc.replace("www.", "").replace("spaceclip.io", "api.spaceclip.io")
                    return f"{parsed.scheme}://{netloc}"
        
        # Fallback: construct from host and port
        if self.host == "0.0.0.0":
            # Use localhost for development
            return f"http://localhost:{self.port}"
        return f"http://{self.host}:{self.port}"
    
    # CORS - parse from comma-separated string (required in production)
    allowed_origins: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins (comma-separated string from ALLOWED_ORIGINS env var)"
    )
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse allowed_origins from comma-separated string or list"""
        if isinstance(v, str):
            # Split comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if v is None:
            return []
        return v
    
    @model_validator(mode="after")
    def set_default_origins(self):
        """Set default origins for development only"""
        # In development, default to frontend_url if not set
        # In production/staging, ALLOWED_ORIGINS must be explicitly set
        if not self.allowed_origins and self.environment == "development" and self.frontend_url:
            self.allowed_origins = [self.frontend_url]
        return self
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_public_url(request=None) -> str:
    """
    Get the public URL for the API from request or settings.
    
    This function:
    1. First checks settings.public_api_url if set
    2. Then tries to derive from request headers (X-Forwarded-Host, X-Forwarded-Proto, Host)
    3. Falls back to settings.get_api_base_url()
    
    Args:
        request: Optional FastAPI Request object. If provided, will try to derive URL from headers.
        
    Returns:
        Base URL string (without trailing slash)
    """
    # Priority 1: Use explicit public_api_url from settings
    if settings.public_api_url:
        return settings.public_api_url.rstrip("/")
    
    # Priority 2: Derive from request headers (for reverse proxy scenarios)
    if request is not None:
        # Check for X-Forwarded-Host (set by reverse proxies like nginx)
        forwarded_host = request.headers.get("X-Forwarded-Host")
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        
        if forwarded_host:
            # X-Forwarded-Host can contain port, so use it as-is
            return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
        
        # Check Host header
        host = request.headers.get("Host")
        if host:
            # Determine protocol from X-Forwarded-Proto or default to http
            # In production behind HTTPS proxy, X-Forwarded-Proto should be set
            proto = request.headers.get("X-Forwarded-Proto", "http")
            return f"{proto}://{host}".rstrip("/")
        
        # Try to get from request.url (FastAPI Request object)
        if hasattr(request, "url"):
            url = request.url
            return f"{url.scheme}://{url.netloc}".rstrip("/")
    
    # Priority 3: Fall back to settings-based derivation
    return settings.get_api_base_url()


def validate_settings(settings: Settings) -> None:
    """Validate critical settings and raise errors if missing"""
    errors = []
    
    if not settings.secret_key:
        errors.append("SECRET_KEY is required but not set")
    
    if not settings.database_url:
        errors.append("DATABASE_URL is required but not set")
    
    if not settings.frontend_url:
        errors.append("FRONTEND_URL is required but not set")
    
    # SECRET_KEY is required in production and staging (for HMAC token validation)
    if settings.environment in ("production", "staging"):
        if not settings.secret_key:
            errors.append(
                f"SECRET_KEY is required in {settings.environment} environment but not set. "
                "Session tokens use HMAC signatures that require a secret key."
            )
    
    # ALLOWED_ORIGINS is required in production and staging
    if settings.environment in ("production", "staging"):
        if not settings.allowed_origins:
            errors.append(
                f"ALLOWED_ORIGINS is required in {settings.environment} environment but not set. "
                "Set it as a comma-separated list, e.g., ALLOWED_ORIGINS=https://spaceclip.io,https://www.spaceclip.io"
            )
    
    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)


# Create settings instance
settings = Settings()

# Validate critical settings
validate_settings(settings)

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)





