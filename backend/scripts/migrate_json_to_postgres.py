"""
Migration script to migrate JSON data to PostgreSQL

This script reads existing JSON files and migrates them to the database.
Run with: python -m scripts.migrate_json_to_postgres

Usage:
    cd backend
    python -m scripts.migrate_json_to_postgres
    python -m scripts.migrate_json_to_postgres --dry-run  # Preview only
"""
import asyncio
import json
import logging
import argparse
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional
from uuid import UUID
import sys

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from config import settings
from models.database import async_session_maker, async_engine
from models.user_model import UserModel
from models.password_model import PasswordHashModel
from models.session_model import SessionModel
from models.project_model import ProjectModel
from models.media_model import MediaModel
from models.transcription_model import TranscriptionModel, TranscriptSegmentModel
from models.highlight_model import HighlightModel
from models.clip_model import ClipModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# JSON Loading Functions
# =============================================================================

def load_users_json(stats: Optional[MigrationStats] = None) -> Optional[dict]:
    """Load users from users.json"""
    users_file = settings.upload_dir / "users.json"
    
    if not users_file.exists():
        logger.warning(f"users.json not found at {users_file}")
        return None
    
    try:
        with open(users_file, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict):
            error = f"users.json is not a dictionary (got {type(data).__name__})"
            logger.error(error)
            if stats:
                stats.add_invalid_file(str(users_file), error)
            return None
        
        logger.info(f"Loaded {len(data)} users from users.json")
        return data
    except json.JSONDecodeError as e:
        error = f"Invalid JSON: {e}"
        logger.error(f"Failed to load users.json: {error}")
        if stats:
            stats.add_invalid_file(str(users_file), error)
        return None
    except Exception as e:
        error = f"Unexpected error: {e}"
        logger.error(f"Failed to load users.json: {error}")
        if stats:
            stats.add_invalid_file(str(users_file), error)
        return None


def load_sessions_json(stats: Optional[MigrationStats] = None) -> Optional[dict]:
    """Load sessions from sessions.json"""
    sessions_file = settings.upload_dir / "sessions.json"
    
    if not sessions_file.exists():
        logger.warning(f"sessions.json not found at {sessions_file}")
        return None
    
    try:
        with open(sessions_file, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict):
            error = f"sessions.json is not a dictionary (got {type(data).__name__})"
            logger.error(error)
            if stats:
                stats.add_invalid_file(str(sessions_file), error)
            return None
        
        logger.info(f"Loaded {len(data)} sessions from sessions.json")
        return data
    except json.JSONDecodeError as e:
        error = f"Invalid JSON: {e}"
        logger.error(f"Failed to load sessions.json: {error}")
        if stats:
            stats.add_invalid_file(str(sessions_file), error)
        return None
    except Exception as e:
        error = f"Unexpected error: {e}"
        logger.error(f"Failed to load sessions.json: {error}")
        if stats:
            stats.add_invalid_file(str(sessions_file), error)
        return None


def load_user_projects_json(stats: Optional[MigrationStats] = None) -> Optional[dict]:
    """Load user projects from user_projects.json"""
    projects_file = settings.upload_dir / "user_projects.json"
    
    if not projects_file.exists():
        logger.warning(f"user_projects.json not found at {projects_file}")
        return None
    
    try:
        with open(projects_file, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict):
            error = f"user_projects.json is not a dictionary (got {type(data).__name__})"
            logger.error(error)
            if stats:
                stats.add_invalid_file(str(projects_file), error)
            return None
        
        logger.info(f"Loaded {len(data)} user projects from user_projects.json")
        return data
    except json.JSONDecodeError as e:
        error = f"Invalid JSON: {e}"
        logger.error(f"Failed to load user_projects.json: {error}")
        if stats:
            stats.add_invalid_file(str(projects_file), error)
        return None
    except Exception as e:
        error = f"Unexpected error: {e}"
        logger.error(f"Failed to load user_projects.json: {error}")
        if stats:
            stats.add_invalid_file(str(projects_file), error)
        return None


def load_project_json_files(stats: Optional[MigrationStats] = None) -> list[dict]:
    """Load all project JSON files from uploads/projects/"""
    projects_dir = settings.upload_dir / "projects"
    
    if not projects_dir.exists():
        logger.warning(f"Projects directory not found at {projects_dir}")
        return []
    
    project_files = list(projects_dir.glob("*.json"))
    logger.info(f"Found {len(project_files)} project JSON files")
    
    projects = []
    for project_file in project_files:
        try:
            with open(project_file, 'r') as f:
                data = json.load(f)
            
            # Validate structure - should be a dict with at least 'media' or 'media_id'
            if not isinstance(data, dict):
                error = f"Not a dictionary (got {type(data).__name__})"
                logger.error(f"Invalid structure in {project_file}: {error}")
                if stats:
                    stats.add_invalid_file(str(project_file), error)
                continue
            
            # Check for required fields
            media_data = data.get('media')
            media_id = data.get('media_id')
            
            if not media_data and not media_id:
                # Try to extract from filename as fallback
                potential_id = project_file.stem
                if not safe_uuid(potential_id):
                    error = "Missing 'media' or 'media_id' field, and filename is not a valid UUID"
                    logger.warning(f"Warning for {project_file}: {error}")
                    if stats:
                        stats.add_invalid_file(str(project_file), error)
                    continue
            
            data['_source_file'] = str(project_file)
            projects.append(data)
        except json.JSONDecodeError as e:
            error = f"Invalid JSON: {e}"
            logger.error(f"Failed to load {project_file}: {error}")
            if stats:
                stats.add_invalid_file(str(project_file), error)
        except Exception as e:
            error = f"Unexpected error: {e}"
            logger.error(f"Failed to load {project_file}: {error}")
            if stats:
                stats.add_invalid_file(str(project_file), error)
    
    logger.info(f"Loaded {len(projects)} valid project files")
    if stats and len(project_files) > len(projects):
        logger.warning(f"  ({len(project_files) - len(projects)} files were invalid or skipped)")
    
    return projects


# =============================================================================
# Utility Functions
# =============================================================================

def parse_datetime(value: Optional[str]) -> datetime:
    """Parse datetime string or return current time"""
    if not value:
        return datetime.utcnow()
    
    try:
        # Try ISO format first
        if 'T' in value:
            return datetime.fromisoformat(value.replace('Z', '+00:00').replace('+00:00', ''))
        # Try other common formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    except Exception:
        pass
    
    return datetime.utcnow()


def safe_uuid(value: Optional[str]) -> Optional[UUID]:
    """Safely convert string to UUID"""
    if not value:
        return None
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert to float"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert to int"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# =============================================================================
# Migration Counters
# =============================================================================

class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.users_created = 0
        self.users_skipped = 0
        self.password_hashes_created = 0
        self.password_hashes_skipped = 0
        self.sessions_created = 0
        self.sessions_skipped = 0
        self.projects_created = 0
        self.media_created = 0
        self.transcriptions_created = 0
        self.segments_created = 0
        self.highlights_created = 0
        self.clips_created = 0
        self.errors = 0
        
        # Track invalid/mismatched JSON files
        self.invalid_json_files: list[dict] = []  # List of {file: path, error: str}
    
    def add_invalid_file(self, file_path: str, error: str):
        """Record an invalid or mismatched JSON file"""
        self.invalid_json_files.append({
            'file': file_path,
            'error': error
        })
    
    def print_summary(self, dry_run: bool = False):
        """Print comprehensive migration summary"""
        mode = "DRY RUN" if dry_run else "MIGRATION"
        logger.info("\n" + "="*70)
        logger.info(f"{mode} SUMMARY REPORT")
        logger.info("="*70)
        
        # Users section
        logger.info("\n📊 USERS:")
        logger.info(f"  ✅ Total inserted: {self.users_created}")
        logger.info(f"  ⏭️  Skipped (already exists): {self.users_skipped}")
        logger.info(f"  🔐 Password hashes inserted: {self.password_hashes_created}")
        
        # Projects section
        logger.info("\n📁 PROJECTS:")
        logger.info(f"  ✅ User projects (folders) created: {self.projects_created}")
        logger.info(f"  ✅ Media projects created: {self.media_created}")
        logger.info(f"  📝 Transcriptions created: {self.transcriptions_created}")
        logger.info(f"  📄 Transcript segments created: {self.segments_created}")
        logger.info(f"  ⭐ Highlights created: {self.highlights_created}")
        logger.info(f"  🎬 Clips created: {self.clips_created}")
        
        # Sessions
        logger.info("\n🔐 SESSIONS:")
        logger.info(f"  ✅ Created: {self.sessions_created}")
        logger.info(f"  ⏭️  Skipped: {self.sessions_skipped}")
        
        # Invalid files section
        if self.invalid_json_files:
            logger.info("\n⚠️  INVALID/MISMATCHED JSON FILES:")
            for invalid in self.invalid_json_files:
                logger.warning(f"  ❌ {invalid['file']}")
                logger.warning(f"     Error: {invalid['error']}")
            logger.info(f"\n  Total invalid files: {len(self.invalid_json_files)}")
        else:
            logger.info("\n✅ All JSON files were valid and processed successfully")
        
        # Errors
        if self.errors > 0:
            logger.warning(f"\n⚠️  Total errors encountered: {self.errors}")
        
        logger.info("\n" + "="*70)
        
        # Final summary line
        total_inserted = self.users_created + self.projects_created + self.media_created
        logger.info(f"\n📈 SUMMARY:")
        logger.info(f"  • Total users inserted: {self.users_created}")
        logger.info(f"  • Total projects inserted: {self.projects_created + self.media_created}")
        logger.info(f"  • Invalid JSON files: {len(self.invalid_json_files)}")
        logger.info("="*70 + "\n")


# =============================================================================
# User Migration
# =============================================================================

async def migrate_user(
    db: AsyncSession,
    user_id: str,
    user_data: dict,
    stats: MigrationStats,
    dry_run: bool = False
) -> Optional[UUID]:
    """
    Migrate a single user, skipping if email already exists.
    Returns the database UUID for the user (existing or newly created).
    """
    email = user_data.get('email')
    wallet_address = user_data.get('wallet_address')
    
    if not email and not wallet_address:
        logger.warning(f"User {user_id} has no email or wallet - skipping")
        stats.users_skipped += 1
        return None
    
    try:
        # Check if user exists by email (primary check)
        existing_user = None
        if email:
            stmt = select(UserModel).where(UserModel.email == email)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info(f"User with email '{email}' already exists - skipping")
                stats.users_skipped += 1
                return existing_user.id
        
        # If not found by email, check wallet address
        if not existing_user and wallet_address:
            stmt = select(UserModel).where(UserModel.wallet_address == wallet_address)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info(f"User with wallet '{wallet_address}' already exists - skipping")
                stats.users_skipped += 1
                return existing_user.id
        
        # Create new user (email doesn't exist)
        user_uuid = safe_uuid(user_id)
        
        if not dry_run:
            new_user = UserModel(
                id=user_uuid or None,
                email=email,
                wallet_address=wallet_address,
                name=user_data.get('name'),
                avatar_url=user_data.get('avatar_url'),
                auth_provider=user_data.get('auth_provider', 'email'),
                created_at=parse_datetime(user_data.get('created_at')),
                updated_at=parse_datetime(user_data.get('updated_at')),
            )
            db.add(new_user)
            await db.flush()
            user_uuid = new_user.id
        
        logger.info(f"Inserted new user: {email or wallet_address}")
        stats.users_created += 1
        return user_uuid
    
    except Exception as e:
        logger.error(f"Failed to migrate user {user_id}: {e}")
        stats.errors += 1
        return None


async def migrate_password_hash(
    db: AsyncSession,
    user_id: UUID,
    password_hash: str,
    stats: MigrationStats,
    dry_run: bool = False
) -> bool:
    """Migrate password hash for a user, skipping if already exists"""
    if not password_hash:
        return False
    
    try:
        # Check if already exists
        stmt = select(PasswordHashModel).where(PasswordHashModel.user_id == user_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.debug(f"Password hash already exists for user {user_id} - skipping")
            stats.password_hashes_skipped += 1
            return True
        
        if not dry_run:
            new_hash = PasswordHashModel(
                user_id=user_id,
                password_hash=password_hash,
                created_at=datetime.utcnow(),
            )
            db.add(new_hash)
            await db.flush()
        
        logger.debug(f"Inserted password hash for user {user_id}")
        stats.password_hashes_created += 1
        return True
    
    except Exception as e:
        logger.error(f"Failed to migrate password hash for user {user_id}: {e}")
        stats.errors += 1
        return False


# =============================================================================
# Session Migration
# =============================================================================

async def migrate_session(
    db: AsyncSession,
    session_data: dict,
    user_id_map: dict[str, UUID],
    stats: MigrationStats,
    dry_run: bool = False
) -> bool:
    """Migrate a single session"""
    json_user_id = session_data.get('user_id')
    token = session_data.get('token')
    
    if not json_user_id or not token:
        stats.sessions_skipped += 1
        return False
    
    # Map JSON user_id to database UUID
    db_user_id = user_id_map.get(json_user_id)
    if not db_user_id:
        logger.warning(f"Session references unknown user {json_user_id} - skipping")
        stats.sessions_skipped += 1
        return False
    
    try:
        # Check if token already exists
        stmt = select(SessionModel).where(SessionModel.token == token)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            logger.debug(f"Session token already exists - skipping")
            stats.sessions_skipped += 1
            return True
        
        if not dry_run:
            new_session = SessionModel(
                id=safe_uuid(session_data.get('id')) or None,
                user_id=db_user_id,
                token=token,
                ip_address=session_data.get('ip_address'),
                user_agent=session_data.get('user_agent'),
                created_at=parse_datetime(session_data.get('created_at')),
                last_active_at=parse_datetime(session_data.get('last_active_at')),
                expires_at=parse_datetime(session_data.get('expires_at')),
            )
            db.add(new_session)
            await db.flush()
        
        stats.sessions_created += 1
        return True
    
    except Exception as e:
        logger.error(f"Failed to migrate session: {e}")
        stats.errors += 1
        return False


# =============================================================================
# Project Migration (User Projects)
# =============================================================================

async def migrate_user_project(
    db: AsyncSession,
    project_id: str,
    project_data: dict,
    user_id_map: dict[str, UUID],
    stats: MigrationStats,
    dry_run: bool = False
) -> Optional[UUID]:
    """Migrate a user project (folder)"""
    json_user_id = project_data.get('user_id')
    
    if not json_user_id:
        logger.warning(f"Project {project_id} has no user_id - skipping")
        return None
    
    db_user_id = user_id_map.get(json_user_id)
    if not db_user_id:
        logger.warning(f"Project references unknown user {json_user_id} - skipping")
        return None
    
    try:
        project_uuid = safe_uuid(project_id)
        
        # Check if project exists
        if project_uuid:
            stmt = select(ProjectModel).where(ProjectModel.id == project_uuid)
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                logger.debug(f"Project {project_id} already exists - skipping")
                return project_uuid
        
        if not dry_run:
            new_project = ProjectModel(
                id=project_uuid or None,
                user_id=db_user_id,
                name=project_data.get('name', 'Untitled'),
                description=project_data.get('description'),
                color=project_data.get('color', '#7c3aed'),
                icon=project_data.get('icon'),
                status=project_data.get('status', 'active'),
                created_at=parse_datetime(project_data.get('created_at')),
                updated_at=parse_datetime(project_data.get('updated_at')),
            )
            db.add(new_project)
            await db.flush()
            project_uuid = new_project.id
        
        stats.projects_created += 1
        return project_uuid
    
    except Exception as e:
        logger.error(f"Failed to migrate project {project_id}: {e}")
        stats.errors += 1
        return None


# =============================================================================
# Project File Migration Result
# =============================================================================

@dataclass
class ProjectFileMigrationResult:
    """Result of migrating a single project file"""
    media_id: Optional[str] = None
    source_file: Optional[str] = None
    
    # Counts
    media_inserted: int = 0
    media_updated: int = 0
    media_skipped: int = 0
    transcription_inserted: int = 0
    transcription_updated: int = 0
    segments_inserted: int = 0
    segments_deleted: int = 0
    highlights_inserted: int = 0
    highlights_deleted: int = 0
    clips_inserted: int = 0
    clips_skipped: int = 0
    
    # Status
    success: bool = False
    error: Optional[str] = None
    
    def print_summary(self):
        """Print summary of this migration"""
        status = "SUCCESS" if self.success else "FAILED"
        logger.info(f"  [{status}] {self.media_id or 'unknown'}")
        if self.source_file:
            logger.info(f"    Source: {self.source_file}")
        logger.info(f"    Media: {self.media_inserted} inserted, {self.media_updated} updated, {self.media_skipped} skipped")
        logger.info(f"    Transcription: {self.transcription_inserted} inserted, {self.transcription_updated} updated")
        logger.info(f"    Segments: {self.segments_inserted} inserted, {self.segments_deleted} replaced")
        logger.info(f"    Highlights: {self.highlights_inserted} inserted, {self.highlights_deleted} replaced")
        logger.info(f"    Clips: {self.clips_inserted} inserted, {self.clips_skipped} skipped (already exist)")
        if self.error:
            logger.error(f"    Error: {self.error}")


# =============================================================================
# Media Project Migration (from uploads/projects/*.json)
# =============================================================================

async def migrate_project_file(
    db: AsyncSession,
    path: Path,
    dry_run: bool = False
) -> ProjectFileMigrationResult:
    """
    Migrate a single project JSON file to the database.
    
    Loads uploads/projects/{id}.json and:
    - Inserts or updates MediaModel
    - Inserts TranscriptionModel + TranscriptSegmentModel (replaces existing)
    - Inserts HighlightModel rows (replaces existing)
    - Inserts ClipModel rows (additive, skips existing)
    
    Args:
        db: Database session
        path: Path to the project JSON file
        dry_run: If True, don't make changes
        
    Returns:
        ProjectFileMigrationResult with summary counts
    """
    result = ProjectFileMigrationResult(source_file=str(path))
    
    # Load JSON file
    try:
        with open(path, 'r') as f:
            project_json = json.load(f)
    except FileNotFoundError:
        result.error = f"File not found: {path}"
        return result
    except json.JSONDecodeError as e:
        result.error = f"Invalid JSON: {e}"
        return result
    
    # Extract media_id from JSON or filename
    media_data = project_json.get('media')
    media_id_str = None
    
    # Try to get media_id from media.id first
    if media_data and media_data.get('id'):
        media_id_str = media_data.get('id')
    else:
        # Fallback: extract from filename (e.g., "abc123.json" -> "abc123")
        media_id_str = path.stem
    
    result.media_id = media_id_str
    
    if not media_id_str:
        result.error = "No media_id found in JSON or filename"
        return result
    
    media_uuid = safe_uuid(media_id_str)
    if not media_uuid:
        result.error = f"Invalid media_id format: {media_id_str}"
        return result
    
    try:
        # Check if media already exists
        stmt = select(MediaModel).where(MediaModel.id == media_uuid)
        db_result = await db.execute(stmt)
        existing_media = db_result.scalar_one_or_none()
        
        if existing_media:
            # Update existing media
            if not dry_run:
                existing_media.status = project_json.get('status', existing_media.status)
                existing_media.progress = safe_float(project_json.get('progress'), existing_media.progress)
                existing_media.error = project_json.get('error')
                existing_media.updated_at = datetime.utcnow()
                
                if media_data:
                    existing_media.filename = media_data.get('filename', existing_media.filename)
                    existing_media.original_filename = media_data.get('original_filename', existing_media.original_filename)
                    existing_media.file_path = media_data.get('file_path', existing_media.file_path)
                    existing_media.thumbnail_path = media_data.get('thumbnail_path', existing_media.thumbnail_path)
                    existing_media.media_type = media_data.get('media_type', existing_media.media_type)
                    existing_media.source_type = media_data.get('source_type', existing_media.source_type)
                    existing_media.source_url = media_data.get('source_url', existing_media.source_url)
                    existing_media.duration = safe_float(media_data.get('duration'), existing_media.duration)
                
                await db.flush()
            
            result.media_updated = 1
            logger.info(f"Updated existing media: {media_id_str}")
        
        elif media_data:
            # Create new media record
            if not dry_run:
                new_media = MediaModel(
                    id=media_uuid,
                    project_id=None,  # Not associated with user project yet
                    filename=media_data.get('filename', ''),
                    original_filename=media_data.get('original_filename'),
                    file_path=media_data.get('file_path', ''),
                    thumbnail_path=media_data.get('thumbnail_path'),
                    media_type=media_data.get('media_type', 'audio'),
                    source_type=media_data.get('source_type', 'upload'),
                    source_url=media_data.get('source_url'),
                    duration=safe_float(media_data.get('duration')),
                    status=project_json.get('status', 'pending'),
                    progress=safe_float(project_json.get('progress')),
                    error=project_json.get('error'),
                    created_at=parse_datetime(media_data.get('created_at')),
                    updated_at=datetime.utcnow(),
                )
                db.add(new_media)
                await db.flush()
            
            result.media_inserted = 1
            logger.info(f"Inserted new media: {media_id_str}")
        
        else:
            # No media data in JSON
            result.media_skipped = 1
            logger.warning(f"No media data in {path} - skipping media insert")
        
        # Migrate transcription if present (replace existing)
        transcription_data = project_json.get('transcription')
        if transcription_data:
            trans_result = await _migrate_project_transcription(
                db, media_uuid, transcription_data, dry_run
            )
            result.transcription_inserted = trans_result.get('inserted', 0)
            result.transcription_updated = trans_result.get('updated', 0)
            result.segments_inserted = trans_result.get('segments_inserted', 0)
            result.segments_deleted = trans_result.get('segments_deleted', 0)
        
        # Migrate highlights if present (replace existing)
        highlights_data = project_json.get('highlights')
        if highlights_data:
            high_result = await _migrate_project_highlights(
                db, media_uuid, highlights_data, dry_run
            )
            result.highlights_inserted = high_result.get('inserted', 0)
            result.highlights_deleted = high_result.get('deleted', 0)
        
        # Migrate clips if present (additive)
        clips_data = project_json.get('clips')
        if clips_data:
            clips_result = await _migrate_project_clips(
                db, media_uuid, clips_data, dry_run
            )
            result.clips_inserted = clips_result.get('inserted', 0)
            result.clips_skipped = clips_result.get('skipped', 0)
        
        result.success = True
        return result
    
    except Exception as e:
        result.error = str(e)
        logger.error(f"Failed to migrate project file {path}: {e}")
        return result


async def _migrate_project_transcription(
    db: AsyncSession,
    media_id: UUID,
    transcription_data: dict,
    dry_run: bool = False
) -> dict:
    """
    Migrate transcription for a media item.
    Replaces existing transcription and segments.
    """
    counts = {
        'inserted': 0,
        'updated': 0,
        'segments_inserted': 0,
        'segments_deleted': 0,
    }
    
    try:
        # Check for existing transcription
        stmt = select(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Delete existing (cascade deletes segments)
            if not dry_run:
                # Count existing segments for stats
                seg_stmt = select(func.count()).select_from(TranscriptSegmentModel).where(
                    TranscriptSegmentModel.transcription_id == existing.id
                )
                seg_result = await db.execute(seg_stmt)
                counts['segments_deleted'] = seg_result.scalar() or 0
                
                await db.delete(existing)
                await db.flush()
            counts['updated'] = 1
        
        # Create new transcription
        if not dry_run:
            new_transcription = TranscriptionModel(
                media_id=media_id,
                language=transcription_data.get('language', 'en'),
                full_text=transcription_data.get('full_text', ''),
                created_at=datetime.utcnow(),
            )
            db.add(new_transcription)
            await db.flush()
            
            # Create segments
            segments = transcription_data.get('segments', [])
            for seg in segments:
                new_segment = TranscriptSegmentModel(
                    transcription_id=new_transcription.id,
                    segment_index=safe_int(seg.get('id', 0)),
                    start_time=safe_float(seg.get('start')),
                    end_time=safe_float(seg.get('end')),
                    text=seg.get('text', ''),
                    speaker=seg.get('speaker'),
                    confidence=safe_float(seg.get('confidence'), 1.0),
                )
                db.add(new_segment)
                counts['segments_inserted'] += 1
            
            await db.flush()
        
        if counts['updated'] == 0:
            counts['inserted'] = 1
        
        logger.debug(f"Migrated transcription for {media_id}: {counts['segments_inserted']} segments")
        return counts
    
    except Exception as e:
        logger.error(f"Failed to migrate transcription for {media_id}: {e}")
        raise


async def _migrate_project_highlights(
    db: AsyncSession,
    media_id: UUID,
    highlights_data: dict,
    dry_run: bool = False
) -> dict:
    """
    Migrate highlights for a media item.
    Replaces existing highlights.
    """
    counts = {
        'inserted': 0,
        'deleted': 0,
    }
    
    try:
        # Delete existing highlights
        if not dry_run:
            del_stmt = select(func.count()).select_from(HighlightModel).where(
                HighlightModel.media_id == media_id
            )
            del_result = await db.execute(del_stmt)
            counts['deleted'] = del_result.scalar() or 0
            
            await db.execute(
                delete(HighlightModel).where(HighlightModel.media_id == media_id)
            )
            await db.flush()
        
        # Insert new highlights
        highlights_list = highlights_data.get('highlights', [])
        
        if not dry_run:
            for h in highlights_list:
                new_highlight = HighlightModel(
                    media_id=media_id,
                    highlight_id=h.get('id', ''),
                    start_time=safe_float(h.get('start')),
                    end_time=safe_float(h.get('end')),
                    title=h.get('title', ''),
                    description=h.get('description', ''),
                    score=safe_float(h.get('score')),
                    tags=h.get('tags', []),
                    transcript_segment_ids=h.get('transcript_segment_ids', []),
                    created_at=parse_datetime(highlights_data.get('analyzed_at')),
                )
                db.add(new_highlight)
                counts['inserted'] += 1
            
            await db.flush()
        
        logger.debug(f"Migrated highlights for {media_id}: {counts['inserted']} inserted, {counts['deleted']} replaced")
        return counts
    
    except Exception as e:
        logger.error(f"Failed to migrate highlights for {media_id}: {e}")
        raise


async def _migrate_project_clips(
    db: AsyncSession,
    media_id: UUID,
    clips_data: list[dict],
    dry_run: bool = False
) -> dict:
    """
    Migrate clips for a media item.
    Additive - skips clips that already exist by ID.
    """
    counts = {
        'inserted': 0,
        'skipped': 0,
    }
    
    try:
        # Get existing clip IDs
        stmt = select(ClipModel.id).where(ClipModel.media_id == media_id)
        result = await db.execute(stmt)
        existing_clip_ids = {str(row[0]) for row in result.fetchall()}
        
        if not dry_run:
            for clip in clips_data:
                clip_id_str = clip.get('id')
                clip_uuid = safe_uuid(clip_id_str)
                
                # Skip if already exists
                if clip_id_str and clip_id_str in existing_clip_ids:
                    counts['skipped'] += 1
                    continue
                
                new_clip = ClipModel(
                    id=clip_uuid or None,
                    media_id=media_id,
                    platform=clip.get('platform', 'unknown'),
                    file_path=clip.get('file_path', ''),
                    duration=safe_float(clip.get('duration')),
                    width=safe_int(clip.get('width'), 1080),
                    height=safe_int(clip.get('height'), 1920),
                    has_captions=clip.get('has_captions', False),
                    created_at=parse_datetime(clip.get('created_at')),
                )
                db.add(new_clip)
                counts['inserted'] += 1
            
            await db.flush()
        
        logger.debug(f"Migrated clips for {media_id}: {counts['inserted']} inserted, {counts['skipped']} skipped")
        return counts
    
    except Exception as e:
        logger.error(f"Failed to migrate clips for {media_id}: {e}")
        raise


# Legacy wrapper for stats-based migration (used by main migration flow)
async def migrate_media_project(
    db: AsyncSession,
    project_json: dict,
    stats: MigrationStats,
    dry_run: bool = False
) -> Optional[UUID]:
    """
    Legacy wrapper: Migrate a media project from dict (used by main migration).
    """
    # Create a temp file-like path for the result
    source_file = project_json.get('_source_file', 'unknown')
    
    # Extract media_id
    media_data = project_json.get('media')
    media_id_str = media_data.get('id') if media_data else None
    
    if not media_id_str:
        logger.warning(f"Project JSON has no media_id - skipping")
        return None
    
    media_uuid = safe_uuid(media_id_str)
    if not media_uuid:
        logger.warning(f"Invalid media_id {media_id_str} - skipping")
        return None
    
    # Write temp file and use migrate_project_file
    temp_path = Path(f"/tmp/migrate_{media_id_str}.json")
    try:
        with open(temp_path, 'w') as f:
            json.dump(project_json, f)
        
        result = await migrate_project_file(db, temp_path, dry_run)
        
        # Update global stats
        stats.media_created += result.media_inserted
        stats.transcriptions_created += result.transcription_inserted
        stats.segments_created += result.segments_inserted
        stats.highlights_created += result.highlights_inserted
        stats.clips_created += result.clips_inserted
        
        if not result.success:
            stats.errors += 1
            return None
        
        return media_uuid
    finally:
        if temp_path.exists():
            temp_path.unlink()


# =============================================================================
# Database Summary
# =============================================================================

async def get_table_row_count(db: AsyncSession, model_class) -> int:
    """Get row count for a table"""
    try:
        stmt = select(func.count()).select_from(model_class)
        result = await db.execute(stmt)
        return result.scalar() or 0
    except Exception as e:
        logger.error(f"Failed to count rows in {model_class.__tablename__}: {e}")
        return 0


async def print_database_summary(db: AsyncSession, title: str = "Database Row Counts"):
    """Print summary of current database row counts"""
    logger.info("\n" + "="*60)
    logger.info(f"{title}:")
    logger.info("="*60)
    
    counts = {
        "Users": await get_table_row_count(db, UserModel),
        "Password Hashes": await get_table_row_count(db, PasswordHashModel),
        "Sessions": await get_table_row_count(db, SessionModel),
        "Projects": await get_table_row_count(db, ProjectModel),
        "Media": await get_table_row_count(db, MediaModel),
        "Transcriptions": await get_table_row_count(db, TranscriptionModel),
        "Transcript Segments": await get_table_row_count(db, TranscriptSegmentModel),
        "Highlights": await get_table_row_count(db, HighlightModel),
        "Clips": await get_table_row_count(db, ClipModel),
    }
    
    for name, count in counts.items():
        logger.info(f"  {name}: {count}")
    
    logger.info("="*60 + "\n")


def print_json_summary(
    users_data: Optional[dict],
    sessions_data: Optional[dict],
    user_projects_data: Optional[dict],
    media_projects_data: list[dict]
):
    """Print summary of JSON data to be migrated"""
    logger.info("\n" + "="*60)
    logger.info("JSON Data Summary:")
    logger.info("="*60)
    
    users_count = len(users_data) if users_data else 0
    sessions_count = len(sessions_data) if sessions_data else 0
    user_projects_count = len(user_projects_data) if user_projects_data else 0
    media_projects_count = len(media_projects_data)
    
    logger.info(f"  Users (users.json): {users_count}")
    logger.info(f"  Sessions (sessions.json): {sessions_count}")
    logger.info(f"  User Projects (user_projects.json): {user_projects_count}")
    logger.info(f"  Media Projects (uploads/projects/*.json): {media_projects_count}")
    logger.info("="*60 + "\n")


# =============================================================================
# Main Migration
# =============================================================================

async def migrate_data(dry_run: bool = False):
    """Main migration function"""
    logger.info("\n" + "="*70)
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made to the database")
        logger.info("="*70)
    else:
        logger.info("🚀 MIGRATION MODE - Changes will be committed to the database")
        logger.info("="*70)
    
    logger.info("Starting JSON to PostgreSQL migration...")
    logger.info(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    
    # Initialize stats early to track invalid files during loading
    stats = MigrationStats()
    
    # Load JSON data (pass stats to track invalid files)
    logger.info("\nLoading JSON files...")
    users_data = load_users_json(stats)
    sessions_data = load_sessions_json(stats)
    user_projects_data = load_user_projects_json(stats)
    media_projects_data = load_project_json_files(stats)
    
    # Print JSON summary
    print_json_summary(users_data, sessions_data, user_projects_data, media_projects_data)
    
    user_id_map: dict[str, UUID] = {}  # Maps JSON user_id -> database UUID
    
    async with async_session_maker() as db:
        # Print current database state (before)
        await print_database_summary(db, "Database Row Counts (BEFORE)")
        
        # Step 1: Migrate users
        if users_data:
            logger.info("Step 1: Migrating users and password hashes...")
            for user_id, user_data in users_data.items():
                db_user_id = await migrate_user(db, user_id, user_data, stats, dry_run)
                if db_user_id:
                    user_id_map[user_id] = db_user_id
                    
                    # Migrate password hash if present
                    password_hash = user_data.get('password_hash')
                    if password_hash:
                        await migrate_password_hash(db, db_user_id, password_hash, stats, dry_run)
            
            if not dry_run:
                await db.commit()
            
            logger.info(f"  Users: {stats.users_created} inserted, {stats.users_skipped} skipped (email already exists)")
            logger.info(f"  Password Hashes: {stats.password_hashes_created} inserted, {stats.password_hashes_skipped} skipped")
        
        # Step 2: Migrate sessions
        if sessions_data:
            logger.info("Step 2: Migrating sessions...")
            for token, session_data in sessions_data.items():
                await migrate_session(db, session_data, user_id_map, stats, dry_run)
            
            if not dry_run:
                await db.commit()
            logger.info(f"  Sessions: {stats.sessions_created} created, {stats.sessions_skipped} skipped")
        
        # Step 3: Migrate user projects (folders)
        if user_projects_data:
            logger.info("Step 3: Migrating user projects (folders)...")
            for project_id, project_data in user_projects_data.items():
                await migrate_user_project(db, project_id, project_data, user_id_map, stats, dry_run)
            
            if not dry_run:
                await db.commit()
            logger.info(f"  Projects: {stats.projects_created} created")
        
        # Step 4: Migrate media projects
        if media_projects_data:
            logger.info("Step 4: Migrating media projects...")
            for project_json in media_projects_data:
                try:
                    await migrate_media_project(db, project_json, stats, dry_run)
                except Exception as e:
                    source_file = project_json.get('_source_file', 'unknown')
                    error_msg = f"Migration failed: {e}"
                    logger.error(f"Failed to migrate {source_file}: {error_msg}")
                    stats.add_invalid_file(source_file, error_msg)
                    stats.errors += 1
            
            if not dry_run:
                await db.commit()
            logger.info(f"  Media: {stats.media_created} created")
            logger.info(f"  Transcriptions: {stats.transcriptions_created} created")
            logger.info(f"  Segments: {stats.segments_created} created")
            logger.info(f"  Highlights: {stats.highlights_created} created")
            logger.info(f"  Clips: {stats.clips_created} created")
        
        # Print final database state (after)
        if not dry_run:
            await print_database_summary(db, "Database Row Counts (AFTER)")
        
        # Print comprehensive migration summary
        stats.print_summary(dry_run=dry_run)
    
    if dry_run:
        logger.info("\n" + "="*70)
        logger.info("✅ DRY RUN COMPLETE - No changes were made to the database")
        logger.info("="*70 + "\n")
    else:
        logger.info("\n" + "="*70)
        logger.info("✅ MIGRATION COMPLETE - All changes have been committed")
        logger.info("="*70 + "\n")


async def migrate_single_project(path: str, dry_run: bool = False) -> ProjectFileMigrationResult:
    """
    Migrate a single project file to the database.
    
    Usage:
        python -m scripts.migrate_json_to_postgres --project uploads/projects/abc123.json
    """
    project_path = Path(path)
    
    if not project_path.exists():
        logger.error(f"File not found: {path}")
        result = ProjectFileMigrationResult(source_file=path)
        result.error = "File not found"
        return result
    
    logger.info(f"Migrating single project file: {path}")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    async with async_session_maker() as db:
        # Show before counts
        await print_database_summary(db, "Database Row Counts (BEFORE)")
        
        # Migrate the file
        result = await migrate_project_file(db, project_path, dry_run)
        
        if result.success and not dry_run:
            await db.commit()
        
        # Show after counts
        if not dry_run:
            await print_database_summary(db, "Database Row Counts (AFTER)")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("Single Project Migration Result:")
        logger.info("="*60)
        result.print_summary()
    
    return result


async def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(
        description="Migrate JSON data to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate all JSON files (full migration)
  python -m scripts.migrate_json_to_postgres

  # Preview full migration without making changes
  python -m scripts.migrate_json_to_postgres --dry-run

  # Migrate a single project file
  python -m scripts.migrate_json_to_postgres --project uploads/projects/abc123.json

  # Preview single project migration
  python -m scripts.migrate_json_to_postgres --project uploads/projects/abc123.json --dry-run
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without making changes'
    )
    parser.add_argument(
        '--project',
        type=str,
        metavar='PATH',
        help='Migrate a single project JSON file instead of all files'
    )
    args = parser.parse_args()
    
    try:
        if args.project:
            # Single project migration
            result = await migrate_single_project(args.project, dry_run=args.dry_run)
            if not result.success:
                sys.exit(1)
        else:
            # Full migration
            await migrate_data(dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Close database engine
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
