"""
Authentication service
Supports email, OAuth, and Web3 wallet authentication
"""
import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import settings
from models.user import (
    User, UserSession, Project, AuthProvider,
    LoginRequest, RegisterRequest, WalletLoginRequest
)

logger = logging.getLogger(__name__)

# Simple file-based storage for development
# In production, use PostgreSQL or similar
USERS_FILE = settings.upload_dir / "users.json"
SESSIONS_FILE = settings.upload_dir / "sessions.json"
PROJECTS_FILE = settings.upload_dir / "user_projects.json"


class AuthService:
    """Handles user authentication and session management"""
    
    def __init__(self):
        self._users: dict[str, User] = {}
        self._sessions: dict[str, UserSession] = {}
        self._projects: dict[str, Project] = {}
        self._load_data()
    
    def _load_data(self):
        """Load users and sessions from disk"""
        try:
            if USERS_FILE.exists():
                data = json.loads(USERS_FILE.read_text())
                self._users = {k: User(**v) for k, v in data.items()}
            
            if SESSIONS_FILE.exists():
                data = json.loads(SESSIONS_FILE.read_text())
                self._sessions = {k: UserSession(**v) for k, v in data.items()}
            
            if PROJECTS_FILE.exists():
                data = json.loads(PROJECTS_FILE.read_text())
                self._projects = {k: Project(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load auth data: {e}")
    
    def _save_data(self):
        """Save users and sessions to disk"""
        try:
            USERS_FILE.write_text(json.dumps(
                {k: v.model_dump() for k, v in self._users.items()},
                default=str
            ))
            SESSIONS_FILE.write_text(json.dumps(
                {k: v.model_dump() for k, v in self._sessions.items()},
                default=str
            ))
            PROJECTS_FILE.write_text(json.dumps(
                {k: v.model_dump() for k, v in self._projects.items()},
                default=str
            ))
        except Exception as e:
            logger.error(f"Failed to save auth data: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt with automatic salting"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _generate_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    async def register(self, request: RegisterRequest, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> tuple[User, str]:
        """Register new user with email/password"""
        # Check if email exists
        for user in self._users.values():
            if user.email == request.email:
                raise ValueError("Email already registered")
        
        # Create user
        password_hash = self._hash_password(request.password)
        user = User(
            email=request.email,
            name=request.name or request.email.split('@')[0],
            auth_provider=AuthProvider.EMAIL,
            password_hash=password_hash,
        )
        
        self._users[user.id] = user
        
        # Create session
        token = self._generate_token()
        session = UserSession(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow()
        )
        self._sessions[token] = session
        
        # Create default project
        default_project = Project(
            user_id=user.id,
            name="My Clips",
            description="Default project for your clips"
        )
        self._projects[default_project.id] = default_project
        
        self._save_data()
        
        return user, token
    
    async def login_email(self, request: LoginRequest, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> tuple[User, str]:
        """Login with email/password"""
        # Find user by email
        user = None
        for u in self._users.values():
            if u.email == request.email:
                user = u
                break
        
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not user.password_hash:
            raise ValueError("Invalid email or password")
        
        if not bcrypt.checkpw(request.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise ValueError("Invalid email or password")
        
        # Create session
        token = self._generate_token()
        session = UserSession(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow()
        )
        self._sessions[token] = session
        self._save_data()
        
        return user, token
    
    async def login_wallet(self, request: WalletLoginRequest, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> tuple[User, str]:
        """Login with Web3 wallet signature"""
        # Verify signature (simplified - in production, use web3.py)
        # The message should be a nonce that we generated
        
        # Find or create user by wallet address
        user = None
        for u in self._users.values():
            if u.wallet_address and u.wallet_address.lower() == request.wallet_address.lower():
                user = u
                break
        
        if not user:
            # Create new user for this wallet
            user = User(
                wallet_address=request.wallet_address,
                name=f"{request.wallet_address[:6]}...{request.wallet_address[-4:]}",
                auth_provider=AuthProvider.WALLET,
            )
            self._users[user.id] = user
            
            # Create default project
            default_project = Project(
                user_id=user.id,
                name="My Clips",
            )
            self._projects[default_project.id] = default_project
        
        # Create session
        token = self._generate_token()
        session = UserSession(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow()
        )
        self._sessions[token] = session
        self._save_data()
        
        return user, token
    
    async def refresh_session(self, token: str) -> tuple[User, str]:
        """Refresh an existing session by extending its expiration"""
        session = self._sessions.get(token)
        if not session:
            raise ValueError("Invalid or expired session")
        
        if session.expires_at < datetime.utcnow():
            del self._sessions[token]
            self._save_data()
            raise ValueError("Session expired")
        
        # Extend expiration to 7 days from now
        session.expires_at = datetime.utcnow() + timedelta(days=7)
        session.last_active_at = datetime.utcnow()
        self._save_data()
        
        user = self._users.get(session.user_id)
        if not user:
            raise ValueError("User not found")
        
        return user, token
    
    async def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user from session token"""
        session = self._sessions.get(token)
        if not session:
            return None
        
        if session.expires_at < datetime.utcnow():
            del self._sessions[token]
            self._save_data()
            return None
        
        # Update last_active_at
        session.last_active_at = datetime.utcnow()
        self._save_data()
        
        return self._users.get(session.user_id)
    
    async def logout(self, token: str) -> bool:
        """Logout user by invalidating session"""
        if token in self._sessions:
            del self._sessions[token]
            self._save_data()
            return True
        return False
    
    async def get_user_projects(self, user_id: str) -> list[Project]:
        """Get all projects for a user"""
        return [p for p in self._projects.values() if p.user_id == user_id]
    
    async def create_project(self, user_id: str, name: str, description: str = None, color: str = None) -> Project:
        """Create a new project for user"""
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
            color=color or "#7c3aed"
        )
        self._projects[project.id] = project
        self._save_data()
        return project
    
    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project"""
        project = self._projects.get(project_id)
        if project and project.user_id == user_id:
            del self._projects[project_id]
            self._save_data()
            # Also delete the project files from storage
            from services.project_storage import project_storage
            project_storage.delete_project(project_id)
            return True
        return False
    
    async def archive_project(self, user_id: str, project_id: str) -> bool:
        """Archive a project (soft delete)"""
        project = self._projects.get(project_id)
        if project and project.user_id == user_id:
            # Update project status to archived
            project_dict = project.model_dump()
            project_dict['status'] = 'archived'
            self._projects[project_id] = Project(**project_dict)
            self._save_data()
            return True
        return False
    
    async def unarchive_project(self, user_id: str, project_id: str) -> bool:
        """Unarchive a project"""
        project = self._projects.get(project_id)
        if project and project.user_id == user_id:
            project_dict = project.model_dump()
            project_dict['status'] = 'active'
            self._projects[project_id] = Project(**project_dict)
            self._save_data()
            return True
        return False
    
    async def clear_project_clips(self, user_id: str, project_id: str) -> bool:
        """Clear all clips from a project"""
        project = self._projects.get(project_id)
        if project and project.user_id == user_id:
            # Clear clips from storage
            from services.project_storage import project_storage
            project_storage.clear_project_clips(project_id)
            return True
        return False
    
    def generate_wallet_nonce(self) -> str:
        """Generate nonce for wallet signature"""
        return f"Sign this message to login to SpaceClip: {secrets.token_hex(16)}"
    
    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered"""
        for user in self._users.values():
            if user.email and user.email.lower() == email.lower():
                return True
        return False
    
    async def update_user_avatar(self, user_id: str, avatar_url: str) -> bool:
        """Update user's avatar URL"""
        user = self._users.get(user_id)
        if user:
            # Create updated user with new avatar
            user_dict = user.model_dump()
            user_dict['avatar_url'] = avatar_url
            self._users[user_id] = User(**user_dict)
            self._save_data()
            return True
        return False
    
    async def update_user(self, user_id: str, updates: dict) -> Optional[User]:
        """Update user profile"""
        user = self._users.get(user_id)
        if user:
            user_dict = user.model_dump()
            for key, value in updates.items():
                if hasattr(user, key):
                    user_dict[key] = value
            self._users[user_id] = User(**user_dict)
            self._save_data()
            return self._users[user_id]
        return None


# Singleton
auth_service = AuthService()


