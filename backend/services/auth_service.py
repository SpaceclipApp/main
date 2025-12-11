"""
Authentication service
Supports email, OAuth, and Web3 wallet authentication
Uses PostgreSQL via repository layer
"""
import logging
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import (
    User, UserSession, Project, AuthProvider,
    LoginRequest, RegisterRequest, WalletLoginRequest
)
from models.user_model import UserModel
from models.session_model import SessionModel
from models.password_model import PasswordHashModel
from models.project_model import ProjectModel
from repositories import UserRepository, SessionRepository, ProjectRepository


logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication and session management"""
    
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        project_repository: ProjectRepository,
    ):
        self.user_repo = user_repository
        self.session_repo = session_repository
        self.project_repo = project_repository
    
    # -------------------------------------------------------------------------
    # Conversion helpers: ORM models -> Pydantic models
    # -------------------------------------------------------------------------
    
    def _user_model_to_pydantic(self, user_model: UserModel) -> User:
        """Convert SQLAlchemy UserModel to Pydantic User"""
        return User(
            id=str(user_model.id),
            email=user_model.email,
            wallet_address=user_model.wallet_address,
            name=user_model.name,
            avatar_url=user_model.avatar_url,
            auth_provider=AuthProvider(user_model.auth_provider),
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            # password_hash is intentionally not included in conversion
        )
    
    def _session_model_to_pydantic(self, session_model: SessionModel) -> UserSession:
        """Convert SQLAlchemy SessionModel to Pydantic UserSession"""
        return UserSession(
            id=str(session_model.id),
            user_id=str(session_model.user_id),
            token=session_model.token,
            expires_at=session_model.expires_at,
            created_at=session_model.created_at,
            ip_address=session_model.ip_address,
            user_agent=session_model.user_agent,
            last_active_at=session_model.last_active_at,
        )
    
    def _project_model_to_pydantic(self, project_model: ProjectModel) -> Project:
        """Convert SQLAlchemy ProjectModel to Pydantic Project"""
        return Project(
            id=str(project_model.id),
            user_id=str(project_model.user_id),
            name=project_model.name,
            description=project_model.description,
            color=project_model.color or "#7c3aed",
            icon=project_model.icon,
            status=project_model.status,
            created_at=project_model.created_at,
            updated_at=project_model.updated_at,
        )
    
    # -------------------------------------------------------------------------
    # Password utilities
    # -------------------------------------------------------------------------
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt with automatic salting"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _generate_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------
    
    async def register(
        self,
        db: AsyncSession,
        request: RegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[User, str]:
        """Register new user with email/password"""
        # Check if email exists
        existing_user = await self.user_repo.get_by_email(db, request.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create user model
        user_model = UserModel(
            email=request.email,
            name=request.name or request.email.split('@')[0],
            auth_provider=AuthProvider.EMAIL.value,
        )
        user_model = await self.user_repo.create(db, user_model)
        
        # Create password hash
        password_hash = self._hash_password(request.password)
        password_model = PasswordHashModel(
            user_id=user_model.id,
            password_hash=password_hash,
        )
        await self.user_repo.create_password_hash(db, password_model)
        
        # Create session
        token = self._generate_token()
        session_model = SessionModel(
            user_id=user_model.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow(),
        )
        await self.session_repo.create(db, session_model)
        
        # Create default project
        default_project = ProjectModel(
            user_id=user_model.id,
            name="My Clips",
            description="Default project for your clips",
        )
        await self.project_repo.create(db, default_project)
        
        return self._user_model_to_pydantic(user_model), token
    
    # -------------------------------------------------------------------------
    # Login
    # -------------------------------------------------------------------------
    
    async def login_email(
        self,
        db: AsyncSession,
        request: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[User, str]:
        """Login with email/password"""
        # Find user by email
        user_model = await self.user_repo.get_by_email(db, request.email)
        if not user_model:
            raise ValueError("Invalid email or password")
        
        # Get password hash
        password_model = await self.user_repo.get_password_hash(db, user_model.id)
        if not password_model:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not self._verify_password(request.password, password_model.password_hash):
            raise ValueError("Invalid email or password")
        
        # Create session
        token = self._generate_token()
        session_model = SessionModel(
            user_id=user_model.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow(),
        )
        await self.session_repo.create(db, session_model)
        
        return self._user_model_to_pydantic(user_model), token
    
    async def login_wallet(
        self,
        db: AsyncSession,
        request: WalletLoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[User, str]:
        """Login with Web3 wallet signature"""
        # Verify signature (simplified - in production, use web3.py)
        # The message should be a nonce that we generated
        
        # Find or create user by wallet address (case-insensitive)
        user_model = await self.user_repo.get_by_wallet_address(db, request.wallet_address.lower())
        
        if not user_model:
            # Create new user for this wallet
            user_model = UserModel(
                wallet_address=request.wallet_address.lower(),
                name=f"{request.wallet_address[:6]}...{request.wallet_address[-4:]}",
                auth_provider=AuthProvider.WALLET.value,
            )
            user_model = await self.user_repo.create(db, user_model)
            
            # Create default project
            default_project = ProjectModel(
                user_id=user_model.id,
                name="My Clips",
            )
            await self.project_repo.create(db, default_project)
        
        # Create session
        token = self._generate_token()
        session_model = SessionModel(
            user_id=user_model.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow(),
        )
        await self.session_repo.create(db, session_model)
        
        return self._user_model_to_pydantic(user_model), token
    
    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    
    async def refresh_session(self, db: AsyncSession, token: str) -> tuple[User, str]:
        """Refresh an existing session by extending its expiration"""
        session_model = await self.session_repo.get_by_token(db, token)
        if not session_model:
            raise ValueError("Invalid or expired session")
        
        if session_model.expires_at < datetime.utcnow():
            await self.session_repo.delete_by_token(db, token)
            raise ValueError("Session expired")
        
        # Extend expiration to 7 days from now
        new_expires_at = datetime.utcnow() + timedelta(days=7)
        await self.session_repo.extend_expiration(db, token, new_expires_at)
        
        user_model = await self.user_repo.get_by_id(db, session_model.user_id)
        if not user_model:
            raise ValueError("User not found")
        
        return self._user_model_to_pydantic(user_model), token
    
    async def get_user_by_token(self, db: AsyncSession, token: str) -> Optional[User]:
        """Get user from session token"""
        session_model = await self.session_repo.get_by_token(db, token)
        if not session_model:
            return None
        
        if session_model.expires_at < datetime.utcnow():
            await self.session_repo.delete_by_token(db, token)
            return None
        
        # Update last_active_at
        await self.session_repo.update_last_active(db, token)
        
        user_model = await self.user_repo.get_by_id(db, session_model.user_id)
        if not user_model:
            return None
        
        return self._user_model_to_pydantic(user_model)
    
    async def logout(self, db: AsyncSession, token: str) -> bool:
        """Logout user by invalidating session"""
        return await self.session_repo.delete_by_token(db, token)
    
    # -------------------------------------------------------------------------
    # Email Utilities
    # -------------------------------------------------------------------------
    
    async def email_exists(self, db: AsyncSession, email: str) -> bool:
        """Check if email is already registered"""
        return await self.user_repo.email_exists(db, email.lower())
    
    def generate_wallet_nonce(self) -> str:
        """Generate nonce for wallet signature"""
        return f"Sign this message to login to SpaceClip: {secrets.token_hex(16)}"
    
    # -------------------------------------------------------------------------
    # User Profile
    # -------------------------------------------------------------------------
    
    async def update_user_avatar(self, db: AsyncSession, user_id: str, avatar_url: str) -> bool:
        """Update user's avatar URL"""
        user_model = await self.user_repo.get_by_id(db, UUID(user_id))
        if not user_model:
            return False
        
        user_model.avatar_url = avatar_url
        await self.user_repo.update(db, user_model)
        return True
    
    async def update_user(self, db: AsyncSession, user_id: str, updates: dict) -> Optional[User]:
        """Update user profile"""
        user_model = await self.user_repo.get_by_id(db, UUID(user_id))
        if not user_model:
            return None
        
        # Apply allowed updates
        allowed_fields = {'name', 'avatar_url'}
        for key, value in updates.items():
            if key in allowed_fields and hasattr(user_model, key):
                setattr(user_model, key, value)
        
        await self.user_repo.update(db, user_model)
        return self._user_model_to_pydantic(user_model)
    
    # -------------------------------------------------------------------------
    # Projects
    # -------------------------------------------------------------------------
    
    async def get_user_projects(self, db: AsyncSession, user_id: str) -> list[Project]:
        """Get all projects for a user"""
        projects = await self.project_repo.get_by_user_id(db, UUID(user_id))
        return [self._project_model_to_pydantic(p) for p in projects]
    
    async def create_project(
        self,
        db: AsyncSession,
        user_id: str,
        name: str,
        description: str = None,
        color: str = None
    ) -> Project:
        """Create a new project for user"""
        project_model = ProjectModel(
            user_id=UUID(user_id),
            name=name,
            description=description,
            color=color or "#7c3aed",
        )
        project_model = await self.project_repo.create(db, project_model)
        return self._project_model_to_pydantic(project_model)
    
    async def delete_project(self, db: AsyncSession, user_id: str, project_id: str) -> bool:
        """Delete a project"""
        result = await self.project_repo.delete_by_user(db, UUID(user_id), UUID(project_id))
        if result:
            # Also delete the project files from storage
            from services.project_storage import project_storage
            project_storage.delete_project(project_id)
        return result
    
    async def archive_project(self, db: AsyncSession, user_id: str, project_id: str) -> bool:
        """Archive a project (soft delete)"""
        # First verify user owns the project
        project_model = await self.project_repo.get_by_id(db, UUID(project_id))
        if not project_model or str(project_model.user_id) != user_id:
            return False
        
        return await self.project_repo.update_status(db, UUID(project_id), "archived")
    
    async def unarchive_project(self, db: AsyncSession, user_id: str, project_id: str) -> bool:
        """Unarchive a project"""
        # First verify user owns the project
        project_model = await self.project_repo.get_by_id(db, UUID(project_id))
        if not project_model or str(project_model.user_id) != user_id:
            return False
        
        return await self.project_repo.update_status(db, UUID(project_id), "active")
    
    async def clear_project_clips(self, db: AsyncSession, user_id: str, project_id: str) -> bool:
        """Clear all clips from a project"""
        # First verify user owns the project
        project_model = await self.project_repo.get_by_id(db, UUID(project_id))
        if not project_model or str(project_model.user_id) != user_id:
            return False
        
        # Get all media for this project and clear their clips
        from repositories.project_repository import media_repository, clip_repository
        media_list = await media_repository.get_by_project_id(db, UUID(project_id))
        
        for media in media_list:
            # Get clips to delete their files
            clips = await clip_repository.get_by_media_id(db, media.id)
            from pathlib import Path
            for clip in clips:
                clip_path = Path(clip.file_path)
                if clip_path.exists():
                    clip_path.unlink()
            # Delete clips from database
            await clip_repository.delete_by_media_id(db, media.id)
        
        # Clear media associations from database
        await self.project_repo.clear_project_media(db, UUID(project_id))
        return True


# Create singleton with repository instances
from repositories.user_repository import user_repository
from repositories.session_repository import session_repository
from repositories.project_repository import project_repository

auth_service = AuthService(
    user_repository=user_repository,
    session_repository=session_repository,
    project_repository=project_repository,
)
