"""
User and Project models for multi-user support
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid
import re


class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    WALLET = "wallet"


class User(BaseModel):
    """User account model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[EmailStr] = None
    wallet_address: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: AuthProvider = AuthProvider.EMAIL
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Settings
    default_platforms: list[str] = ["instagram_reels", "tiktok"]
    default_audiogram_style: str = "cosmic"


class Project(BaseModel):
    """Project/folder for organizing media"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None
    color: str = "#7c3aed"  # Default purple
    icon: Optional[str] = None
    status: str = "active"  # active, archived, deleted
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Stats
    media_count: int = 0
    clips_count: int = 0


class MediaProject(BaseModel):
    """Association between media and projects"""
    media_id: str
    project_id: str
    added_at: datetime = Field(default_factory=datetime.utcnow)


class UserSession(BaseModel):
    """User session for auth"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    last_active_at: datetime = Field(default_factory=datetime.utcnow)


class LoginRequest(BaseModel):
    """Email login request"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    name: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters and include a letter and a number.")
        
        has_letter = bool(re.search(r'[a-zA-Z]', v))
        has_digit = bool(re.search(r'[0-9]', v))
        
        if not has_letter or not has_digit:
            raise ValueError("Password must be at least 8 characters and include a letter and a number.")
        
        return v


class WalletLoginRequest(BaseModel):
    """Web3 wallet login request"""
    wallet_address: str
    signature: str
    message: str


class CreateProjectRequest(BaseModel):
    """Create project request"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class UserProfile(BaseModel):
    """Public user profile"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    projects_count: int = 0
    clips_count: int = 0


