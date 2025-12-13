"""
Authentication API routes

⚠️ AUTH SYSTEM DIRECTIVE — DO NOT MODIFY

Spaceclip uses an opaque session-token authentication system.
- Session tokens are stored in the database (sessions table).
- Backend verifies tokens by DB lookups AND HMAC signatures for integrity.
- Do NOT replace with JWT-based login. See docs/AUTH_SYSTEM.md for details.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Depends, File, UploadFile, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import (
    User, Project, UserProfile,
    LoginRequest, RegisterRequest, WalletLoginRequest,
    CreateProjectRequest
)
from models.database import get_db_session
from services.auth_service import auth_service
from config import settings, get_public_url
from logging_context import user_id_var

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter - will be set from app state in main.py
limiter = Limiter(key_func=get_remote_address)


async def db_session_dependency() -> AsyncSession:
    """FastAPI dependency to get a database session."""
    async for session in get_db_session():
        yield session


async def get_current_user(
    authorization: Optional[str] = Header(None),
    request: Request = None,
    db: AsyncSession = Depends(db_session_dependency)
) -> Optional[User]:
    """Dependency to get current user from auth header"""
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    user = await auth_service.get_user_by_token(db, token)
    
    # Set user_id in request state and context for logging
    if user and request:
        request.state.user_id = user.id
        user_id_var.set(str(user.id))
    
    return user


async def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    """Dependency that requires authentication"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


class CheckEmailRequest(BaseModel):
    email: str


@router.post("/check-email")
#@limiter.limit("5/minute")
async def check_email(
    request: CheckEmailRequest,
    http_request: Request,
    db: AsyncSession = Depends(db_session_dependency)
):
    """Check if email already exists"""
    exists = await auth_service.email_exists(db, request.email)
    return {"exists": exists}


@router.post("/register")
#@limiter.limit("5/minute")
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(db_session_dependency)
):
    """Register new user with email/password"""
    try:
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")
        user, token = await auth_service.register(
            db, request, ip_address=ip_address, user_agent=user_agent
        )
        return {
            "user": UserProfile(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                created_at=user.created_at,
            ),
            "token": token
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
#@limiter.limit("5/minute")
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(db_session_dependency)
):
    """Login with email/password"""
    try:
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")
        user, token = await auth_service.login_email(
            db, request, ip_address=ip_address, user_agent=user_agent
        )
        return {
            "user": UserProfile(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                created_at=user.created_at,
            ),
            "token": token
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/wallet/nonce")
async def get_wallet_nonce():
    """Get nonce for wallet signature"""
    nonce = auth_service.generate_wallet_nonce()
    return {"nonce": nonce}


@router.post("/wallet/login")
async def login_wallet(
    request: WalletLoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(db_session_dependency)
):
    """Login with Web3 wallet signature"""
    try:
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")
        user, token = await auth_service.login_wallet(
            db, request, ip_address=ip_address, user_agent=user_agent
        )
        return {
            "user": UserProfile(
                id=user.id,
                name=user.name,
                avatar_url=user.avatar_url,
                created_at=user.created_at,
            ),
            "token": token
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh")
async def refresh_session(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Refresh session token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = parts[1]
    
    try:
        user, token = await auth_service.refresh_session(db, token)
        return {
            "user": UserProfile(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                created_at=user.created_at,
            ),
            "token": token
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(
    user: User = Depends(require_auth),
    authorization: str = Header(),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Logout current user"""
    token = authorization.split()[1]
    await auth_service.logout(db, token)
    return {"status": "logged out"}


class UpdateProfileRequest(BaseModel):
    """Request to update user profile"""
    name: Optional[str] = None
    avatar_url: Optional[str] = None


@router.get("/me")
async def get_current_user_profile(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Get current user profile"""
    projects = await auth_service.get_user_projects(db, user.id)
    return {
        "user": UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            projects_count=len(projects),
        ),
        "settings": {
            "default_platforms": user.default_platforms,
            "default_audiogram_style": user.default_audiogram_style,
        }
    }


@router.patch("/me")
async def update_current_user_profile(
    request: UpdateProfileRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Update current user profile (name, avatar)"""
    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.avatar_url is not None:
        updates['avatar_url'] = request.avatar_url
    
    if not updates:
        # Nothing to update, return current user
        return {
            "user": UserProfile(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                created_at=user.created_at,
            )
        }
    
    updated_user = await auth_service.update_user(db, user.id, updates)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user": UserProfile(
            id=updated_user.id,
            email=updated_user.email,
            name=updated_user.name,
            avatar_url=updated_user.avatar_url,
            created_at=updated_user.created_at,
        )
    }


@router.get("/projects")
async def get_user_projects(user: User = Depends(require_auth), db: AsyncSession = Depends(db_session_dependency)):
    """Get all projects for current user"""
    projects = await auth_service.get_user_projects(db, user.id)
    return {"projects": projects}



@router.post("/projects")
async def create_project(
    request: CreateProjectRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Create a new project"""
    project = await auth_service.create_project(
        db,
        user_id=user.id,
        name=request.name,
        description=request.description,
        color=request.color
    )
    return {"project": project}


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Delete a project permanently"""
    success = await auth_service.delete_project(db, user.id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


@router.post("/projects/{project_id}/archive")
async def archive_project(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Archive a project (soft delete)"""
    success = await auth_service.archive_project(db, user.id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "archived"}


@router.post("/projects/{project_id}/unarchive")
async def unarchive_project(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Unarchive a project"""
    success = await auth_service.unarchive_project(db, user.id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "active"}


@router.post("/projects/{project_id}/clear-clips")
async def clear_project_clips(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Clear all generated clips from a project"""
    success = await auth_service.clear_project_clips(db, user.id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "cleared"}


@router.post("/avatar")
async def upload_avatar(
    http_request: Request,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(db_session_dependency)
):
    """Upload user avatar"""
    import uuid as uuid_lib
    from pathlib import Path
    from config import settings
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")
    
    # Validate file size (max 5MB)
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB allowed.")
    
    # Generate unique filename
    ext = Path(file.filename).suffix if file.filename else '.jpg'
    filename = f"avatar_{uuid_lib.uuid4()}{ext}"
    avatar_path = settings.upload_dir / "avatars" / filename
    
    # Create avatars directory if it doesn't exist
    avatar_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save file
    try:
        with open(avatar_path, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        logger.error(f"Failed to save avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to save avatar")
    
    # Generate URL using get_public_url helper (derives from request or settings)
    public_url = get_public_url(http_request)
    avatar_url = f"{public_url}/uploads/avatars/{filename}"
    
    # Update user if authenticated
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            user = await auth_service.get_user_by_token(db, token)
            if user:
                await auth_service.update_user_avatar(db, user.id, avatar_url)
        except Exception as e:
            logger.error(f"Failed to update user avatar: {e}")
    
    return {"avatar_url": avatar_url}


@router.get("/nfts/{wallet_address}")
async def get_wallet_nfts(wallet_address: str):
    """Get NFTs for a wallet address"""
    import httpx
    
    # Try to fetch NFTs from Alchemy, OpenSea, or other NFT APIs
    # For now, return demo data - in production, integrate with real API
    try:
        # You would integrate with Alchemy/OpenSea here
        # Example: https://docs.alchemy.com/reference/getnfts
        
        # Demo NFTs for development
        demo_nfts = [
            {
                "id": "1",
                "name": "CryptoPunk #1234",
                "image": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={wallet_address[:8]}1",
                "collection": "CryptoPunks"
            },
            {
                "id": "2", 
                "name": "Bored Ape #5678",
                "image": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={wallet_address[:8]}2",
                "collection": "BAYC"
            },
            {
                "id": "3",
                "name": "Doodle #9012",
                "image": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={wallet_address[:8]}3",
                "collection": "Doodles"
            },
            {
                "id": "4",
                "name": "Azuki #3456",
                "image": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={wallet_address[:8]}4",
                "collection": "Azuki"
            },
            {
                "id": "5",
                "name": "CloneX #7890",
                "image": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={wallet_address[:8]}5",
                "collection": "CloneX"
            },
            {
                "id": "6",
                "name": "Moonbird #2345",
                "image": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={wallet_address[:8]}6",
                "collection": "Moonbirds"
            },
        ]
        
        return {"nfts": demo_nfts}
        
    except Exception as e:
        logger.error(f"Failed to fetch NFTs: {e}")
        return {"nfts": [], "error": "Could not fetch NFTs"}
