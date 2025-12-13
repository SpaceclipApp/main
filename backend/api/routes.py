"""
API routes for SpaceClip

DIAGNOSTIC NOTES (Observed Issues - NOT FIXED):
- Multiple concurrent highlight analyses for the same media_id observed in logs
- Sequential clip generation causing perceived slowness (2 platforms × 30s = ~60s minimum)
- Heavy FFmpeg cost per platform (CPU-intensive operations)
- No request deduplication or locking mechanism currently implemented

State clearly: "These are known and verified. No optimization is implemented in this task."
"""
import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import (
    MediaUploadRequest,
    MediaInfo,
    TranscriptionResult,
    HighlightAnalysis,
    ClipRequest,
    ClipResult,
    ProjectState,
    ProjectStatusResponse,
    ProcessingStatus,
    Platform,
)
from models.database import get_db_session
from models.user import User
from services import (
    media_downloader,
    transcription_service,
    highlight_detector,
    clip_generator,
)
from services.project_storage import project_storage
from services.auth_service import auth_service
from api.auth_routes import get_current_user, require_auth
from repositories.project_repository import clip_repository
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory project store (with database persistence)
# Keyed by user_id:media_id to prevent cross-user cache poisoning
projects: dict[str, ProjectState] = {}


def _cache_key(user_id: Optional[str], media_id: str) -> str:
    """Generate cache key that includes user scope"""
    if user_id:
        return f"{user_id}:{media_id}"
    return f"anon:{media_id}"


async def db_session_dependency() -> AsyncSession:
    """FastAPI dependency to get a database session."""
    async for session in get_db_session():
        yield session


async def _get_user_default_project_id(db: AsyncSession, user_id: str) -> Optional[str]:
    """Get or create user's default project and return its ID"""
    from repositories.project_repository import project_repository
    from models.project_model import ProjectModel
    from uuid import UUID
    
    user_uuid = UUID(user_id)
    user_projects = await project_repository.get_by_user_id(db, user_uuid)
    
    if user_projects:
        # Return first project (default)
        return str(user_projects[0].id)
    
    # Create default project for user
    default_project = ProjectModel(
        user_id=user_uuid,
        name="My Clips",
        description="Default project for your clips",
    )
    created = await project_repository.create(db, default_project)
    return str(created.id)


async def _save_project(db: AsyncSession, media_id: str, user_id: Optional[str] = None, project_id: Optional[str] = None):
    """Save project to database"""
    cache_key = _cache_key(user_id, media_id)
    state = None
    if cache_key in projects:
        state = projects[cache_key]
    elif media_id in projects:
        # Legacy cache key support
        state = projects[media_id]

    if state:
        await project_storage.save_project(db, media_id, state, project_id=project_id)


async def _load_or_create_project(
    db: AsyncSession,
    media_id: str,
    user_id: Optional[str] = None,
    current_user: Optional[User] = None,
) -> Optional[ProjectState]:
    """Load project from database or memory with user scoping."""
    cache_key = _cache_key(user_id, media_id)

    # 1) Try user-scoped cache
    if cache_key in projects:
        cached = projects[cache_key]
        # If we have an authenticated user, enforce ownership
        if current_user and cached.user_id and str(cached.user_id) != str(current_user.id):
            return None
        return cached

    # 2) Legacy cache (pre-scoped keys)
    if media_id in projects:
        cached = projects[media_id]
        # Enforce ownership if possible
        if current_user and cached.user_id and str(cached.user_id) != str(current_user.id):
            return None
        # Also promote to scoped key for future lookups
        projects[cache_key] = cached
        return cached

    # 3) Load from DB via project_storage (which also enforces ownership)
    loaded = await project_storage.load_project(db, media_id, user_id=user_id)
    if loaded:
        # Ensure user_id and project_id are set consistently
        if current_user and not loaded.user_id:
            loaded.user_id = str(current_user.id)
        projects[cache_key] = loaded
        return loaded

    return None


@router.post("/upload/file", response_model=MediaInfo)
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Upload a media file (video or audio)"""
    # Get user info for project linking (user must be authenticated)
    user_id = current_user.id
    # Get or create user's default project
    project_id = await _get_user_default_project_id(db, user_id)
    
    # Validate file type
    allowed_extensions = {
        '.mp4', '.mov', '.avi', '.mkv', '.webm',  # Video
        '.mp3', '.m4a', '.wav', '.ogg', '.aac', '.flac'  # Audio
    }
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    temp_path = settings.upload_dir / f"temp_{uuid.uuid4()}{file_ext}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the upload
        media_info = await media_downloader.process_upload(temp_path, file.filename)
        
        # Create project state with user + project scoping
        cache_key = _cache_key(user_id, media_info.id)
        projects[cache_key] = ProjectState(
            user_id=str(user_id) if user_id else None,
            project_id=str(project_id) if project_id else None,
            media=media_info,
            status=ProcessingStatus.PENDING,
        )
        
        # Save to database with project_id linking
        await _save_project(db, media_info.id, user_id, project_id=project_id)
        
        return media_info
        
    except Exception as e:
        # Cleanup on error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/url", response_model=MediaInfo)
async def upload_from_url(
    request: MediaUploadRequest,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Download and process media from URL (YouTube, X Spaces, etc.)"""
    # Get user info for project linking (user must be authenticated)
    user_id = current_user.id
    # Get or create user's default project
    project_id = await _get_user_default_project_id(db, user_id)
    
    try:
        media_info = await media_downloader.download(request.url)
        
        # Create project state with user + project scoping
        cache_key = _cache_key(user_id, media_info.id)
        projects[cache_key] = ProjectState(
            user_id=str(user_id) if user_id else None,
            project_id=str(project_id) if project_id else None,
            media=media_info,
            status=ProcessingStatus.PENDING,
        )
        
        # Save to database with project_id linking
        await _save_project(db, media_info.id, user_id, project_id=project_id)
        
        return media_info
        
    except Exception as e:
        logger.error(f"URL download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe/{media_id}", response_model=TranscriptionResult)
async def transcribe_media(
    media_id: str, 
    language: Optional[str] = None,
    num_speakers: Optional[int] = None,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Transcribe uploaded media with speaker detection"""
    user_id = current_user.id
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    project.status = ProcessingStatus.TRANSCRIBING
    
    try:
        result = await transcription_service.transcribe_with_speakers(
            media_id=media_id,
            file_path=Path(project.media.file_path),
            language=language,
            num_speakers=num_speakers
        )
        
        project.transcription = result
        project.status = ProcessingStatus.PENDING
        
        # Save to database
        await _save_project(db, media_id, user_id=user_id)
        
        return result
        
    except Exception as e:
        project.status = ProcessingStatus.ERROR
        project.error = str(e)
        await _save_project(db, media_id, user_id=user_id)
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{media_id}", response_model=HighlightAnalysis)
async def analyze_highlights(
    media_id: str,
    max_highlights: int = 10,
    min_duration: float = 15.0,
    max_duration: float = 90.0,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    append: bool = False,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """
    Analyze media for highlights using AI
    
    Args:
        max_highlights: Maximum number of highlights to find
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        start_time: Optional start time to analyze specific section
        end_time: Optional end time to analyze specific section
        append: If True, append new highlights to existing ones
    """
    user_id = current_user.id
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if not project.transcription:
        raise HTTPException(
            status_code=400, 
            detail="Media must be transcribed first"
        )
    
    project.status = ProcessingStatus.ANALYZING
    
    try:
        # Determine time range
        time_range = None
        if start_time is not None or end_time is not None:
            total_duration = project.media.duration if project.media else 0
            time_range = (
                start_time if start_time is not None else 0,
                end_time if end_time is not None else total_duration
            )
        
        result = await highlight_detector.analyze(
            media_id=media_id,
            transcription=project.transcription,
            max_highlights=max_highlights,
            min_clip_duration=min_duration,
            max_clip_duration=max_duration,
            time_range=time_range
        )
        
        # Append or replace highlights
        if append and project.highlights:
            # Merge with existing highlights
            existing_ids = {h.id for h in project.highlights.highlights}
            new_highlights = [h for h in result.highlights if h.id not in existing_ids]
            project.highlights.highlights.extend(new_highlights)
            # Re-sort by time
            project.highlights.highlights.sort(key=lambda h: h.start)
            result = project.highlights
        else:
            project.highlights = result
        
        project.status = ProcessingStatus.COMPLETE
        
        # Save to database
        await _save_project(db, media_id, user_id=user_id)
        
        return result
        
    except Exception as e:
        project.status = ProcessingStatus.ERROR
        project.error = str(e)
        await _save_project(db, media_id, user_id=user_id)
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clips", response_model=list[ClipResult])
async def create_clips(
    request: ClipRequest,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Create clips for specified platforms"""
    user_id = current_user.id
    project = await _load_or_create_project(db, request.media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Task 2.5.4: Sanity checks before clip generation
    # Validate clip timestamps are within media bounds
    if request.start < 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Clip start time cannot be negative: {request.start}"
        )
    
    if project.media and request.end > project.media.duration:
        raise HTTPException(
            status_code=400,
            detail=f"Clip end time ({request.end}s) exceeds media duration ({project.media.duration}s)"
        )
    
    if request.start >= request.end:
        raise HTTPException(
            status_code=400,
            detail=f"Clip start time ({request.start}s) must be before end time ({request.end}s)"
        )
    
    clip_duration = request.end - request.start
    if clip_duration < 1:
        raise HTTPException(
            status_code=400,
            detail=f"Clip duration must be at least 1 second, got {clip_duration}s"
        )
    
    # Get captions for the clip range if requested
    captions = None
    if request.include_captions and project.transcription:
        captions = [
            seg for seg in project.transcription.segments
            if seg.start >= request.start and seg.end <= request.end
        ]
    
    # Get existing clips for duplicate checking
    media_uuid = UUID(request.media_id)
    existing_clips = await clip_repository.get_by_media_id(db, media_uuid)
    
    try:
        results = []
        total_clips = len(request.platforms)
        
        # Update project status for progress reporting
        # NOTE: This is for UI transparency only. No optimization or deduplication is implemented.
        project.status = ProcessingStatus.ANALYZING  # Reuse ANALYZING for clip generation
        project.status_message = f"Generating clip 0/{total_clips}..."
        await _save_project(db, request.media_id, user_id=user_id)
        
        for idx, platform in enumerate(request.platforms):
            clip_num = idx + 1
            platform_name = platform.value.replace('_', ' ').title()
            
            # Update progress
            project.status_message = f"Generating clip {clip_num}/{total_clips} ({platform_name})..."
            project.progress = 0.5 + (clip_num / total_clips * 0.4)  # 50-90% range
            await _save_project(db, request.media_id, user_id=user_id)
            
            clip = await clip_generator.create_clip(
                media=project.media,
                start=request.start,
                end=request.end,
                platform=platform,
                captions=captions,
                title=request.title,
                color_scheme=request.audiogram_style or "cosmic",
                check_duplicates=True,
                existing_clips=existing_clips
            )
            results.append(clip)
            # Only append to project.clips if it's a new clip (not a duplicate)
            if clip.id not in [str(c.id) for c in existing_clips]:
                project.clips.append(clip)
        
        # Final status
        project.status_message = f"Generated {len(results)} clip{'s' if len(results) != 1 else ''}"
        project.progress = 1.0
        
        # Save to database
        await _save_project(db, request.media_id, user_id=user_id)
        
        return results
        
    except Exception as e:
        project.status = ProcessingStatus.ERROR
        project.error = str(e)
        await _save_project(db, request.media_id, user_id=user_id)
        logger.error(f"Clip creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{media_id}/captions")
async def get_clip_captions(
    media_id: str,
    start: float = Query(..., description="Clip start time in seconds"),
    end: float = Query(..., description="Clip end time in seconds"),
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """
    Get captions/transcript segments for a specific time range.
    
    Used for:
    - Regenerating captions after manual clip boundary adjustment
    - Previewing captions for a clip before export
    
    Returns segments that overlap with the given time range,
    with timestamps adjusted relative to clip start.
    """
    user_id = current_user.id
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if not project.transcription:
        raise HTTPException(status_code=404, detail="No transcription available")
    
    # Filter segments within range
    segments = []
    for seg in project.transcription.segments:
        # Include segment if it overlaps with the range
        if seg.end > start and seg.start < end:
            # Calculate relative timestamps
            relative_start = max(0, seg.start - start)
            relative_end = min(end - start, seg.end - start)
            
            segments.append({
                "id": seg.id,
                "start": relative_start,
                "end": relative_end,
                "original_start": seg.start,
                "original_end": seg.end,
                "text": seg.text,
                "speaker": seg.speaker,
                "confidence": seg.confidence,
            })
    
    return {
        "media_id": media_id,
        "clip_start": start,
        "clip_end": end,
        "clip_duration": end - start,
        "segments": segments,
        "segment_count": len(segments),
    }


@router.post("/projects/{media_id}/clip-range")
async def update_clip_range(
    media_id: str,
    start: float = Query(..., description="New clip start time"),
    end: float = Query(..., description="New clip end time"),
    highlight_id: Optional[str] = Query(None, description="Associated highlight ID"),
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """
    Update/save the current clip range selection.
    
    This endpoint:
    - Validates the time range
    - Optionally associates with a highlight
    - Returns updated captions for the new range
    
    Used when user drags clip boundary handles to adjust timing.
    """
    user_id = current_user.id
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Validate range
    if start < 0:
        raise HTTPException(status_code=400, detail="Start time cannot be negative")
    
    if project.media and end > project.media.duration:
        raise HTTPException(status_code=400, detail="End time exceeds media duration")
    
    if end <= start:
        raise HTTPException(status_code=400, detail="End time must be greater than start time")
    
    duration = end - start
    if duration < 5:
        raise HTTPException(status_code=400, detail="Clip must be at least 5 seconds")
    
    if duration > 180:
        raise HTTPException(status_code=400, detail="Clip cannot exceed 3 minutes")
    
    # Get captions for new range
    captions = []
    if project.transcription:
        for seg in project.transcription.segments:
            if seg.end > start and seg.start < end:
                captions.append({
                    "id": seg.id,
                    "start": max(0, seg.start - start),
                    "end": min(duration, seg.end - start),
                    "text": seg.text,
                    "speaker": seg.speaker,
                })
    
    # Find matching highlight if ID provided
    highlight_info = None
    if highlight_id and project.highlights:
        for h in project.highlights.highlights:
            if h.id == highlight_id:
                highlight_info = {
                    "id": h.id,
                    "title": h.title,
                    "original_start": h.start,
                    "original_end": h.end,
                }
                break
    
    return {
        "media_id": media_id,
        "start": start,
        "end": end,
        "duration": duration,
        "highlight": highlight_info,
        "captions": captions,
        "caption_count": len(captions),
    }


@router.get("/projects", response_model=list[dict])
async def list_projects(
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth),
):
    """List all saved media for the current user"""

    user_id = current_user.id

    return await project_storage.list_projects(
        db,
        user_id=user_id,
        include_archived=include_archived,
    )


@router.get("/projects/{media_id}", response_model=ProjectState)
async def get_project(
    media_id: str,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Get full project state"""
    user_id = current_user.id
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return project


@router.get("/projects/{media_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(
    media_id: str,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """
    Get lightweight project status for polling.
    
    This endpoint is optimized for frequent polling (every 2s) during processing.
    Returns minimal data needed to update UI progress indicators.
    
    State transitions:
    - PENDING → DOWNLOADING → TRANSCRIBING → ANALYZING → COMPLETE
    - Any state can transition to ERROR
    """
    from datetime import datetime
    
    user_id = current_user.id
    cache_key = _cache_key(user_id, media_id)
    
    # Check in-memory cache first (active processing)
    if cache_key in projects:
        project = projects[cache_key]
        return ProjectStatusResponse(
            media_id=media_id,
            status=project.status,
            progress=project.progress,
            status_message=project.status_message,
            error=project.error,
            has_transcription=project.transcription is not None,
            has_highlights=project.highlights is not None,
            clip_count=len(project.clips),
            updated_at=datetime.utcnow(),
        )
    
    # Fall back to database
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return ProjectStatusResponse(
        media_id=media_id,
        status=project.status,
        progress=project.progress,
        status_message=project.status_message,
        error=project.error,
        has_transcription=project.transcription is not None,
        has_highlights=project.highlights is not None,
        clip_count=len(project.clips),
        updated_at=datetime.utcnow(),
    )


@router.get("/download/{clip_id}")
async def download_clip(clip_id: str):
    """Download a generated clip"""
    # Find the clip
    for project in projects.values():
        for clip in project.clips:
            if clip.id == clip_id:
                file_path = Path(clip.file_path)
                if file_path.exists():
                    return FileResponse(
                        path=file_path,
                        filename=f"spaceclip_{clip.platform.value}_{clip_id[:8]}.mp4",
                        media_type="video/mp4"
                    )
    
    raise HTTPException(status_code=404, detail="Clip not found")


@router.get("/thumbnail/{media_id}")
async def get_thumbnail(media_id: str):
    """Get media thumbnail"""
    if media_id not in projects:
        raise HTTPException(status_code=404, detail="Media not found")
    
    project = projects[media_id]
    
    if project.media.thumbnail_path:
        thumb_path = Path(project.media.thumbnail_path)
        if thumb_path.exists():
            return FileResponse(
                path=thumb_path,
                media_type="image/jpeg"
            )
    
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@router.delete("/projects/{media_id}")
async def delete_project(
    media_id: str,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Delete a project and its files"""
    user_id = current_user.id
    
    # Try to load from database first
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    cache_key = _cache_key(user_id, media_id)
    
    if not project and cache_key not in projects and media_id not in projects:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if not project:
        project = projects.get(cache_key) or projects.get(media_id)
    
    if project:
        # Delete media file
        if project.media:
            media_path = Path(project.media.file_path)
            if media_path.exists():
                media_path.unlink()
            
            # Delete thumbnail
            if project.media.thumbnail_path:
                thumb_path = Path(project.media.thumbnail_path)
                if thumb_path.exists():
                    thumb_path.unlink()
        
        # Delete clips
        for clip in project.clips:
            clip_path = Path(clip.file_path)
            if clip_path.exists():
                clip_path.unlink()
    
    # Delete from database
    await project_storage.delete_project_async(db, media_id, user_id)
    
    # Remove from in-memory store (both keys)
    if cache_key in projects:
        del projects[cache_key]
    if media_id in projects:
        del projects[media_id]
    
    return {"status": "deleted"}


@router.post("/projects/{media_id}/archive")
async def archive_media_project(
    media_id: str,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Archive a media project (soft delete)"""
    user_id = current_user.id
    
    # Update media status to archived
    success = await project_storage.archive_media(db, media_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Remove from cache
    cache_key = _cache_key(user_id, media_id)
    if cache_key in projects:
        del projects[cache_key]
    if media_id in projects:
        del projects[media_id]
    
    return {"status": "archived"}


@router.post("/projects/{media_id}/unarchive")
async def unarchive_media_project(
    media_id: str,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Unarchive a media project"""
    user_id = current_user.id
    
    # Update media status to active
    success = await project_storage.unarchive_media(db, media_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return {"status": "active"}


@router.post("/projects/{media_id}/clear-clips")
async def clear_media_clips(
    media_id: str,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """Clear all generated clips from a media project"""
    user_id = current_user.id
    
    # Clear clips
    success = await project_storage.clear_project_clips(db, media_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Update cache
    cache_key = _cache_key(user_id, media_id)
    if cache_key in projects:
        projects[cache_key].clips = []
    if media_id in projects:
        projects[media_id].clips = []
    
    return {"status": "cleared"}


@router.get("/platforms", response_model=list[dict])
async def get_platforms():
    """Get available export platforms with specs"""
    from models import PLATFORM_SPECS
    
    return [
        {
            "platform": spec.platform.value,
            "width": spec.width,
            "height": spec.height,
            "max_duration": spec.max_duration,
            "aspect_ratio": spec.aspect_ratio
        }
        for spec in PLATFORM_SPECS.values()
    ]


@router.post("/caption")
async def generate_caption(
    text: str,
    platform: str = "twitter"
):
    """Generate AI caption for a clip"""
    try:
        caption = await highlight_detector.generate_caption(text, platform)
        return {"caption": caption}
    except Exception as e:
        logger.error(f"Caption generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background processing endpoint
@router.post("/process/{media_id}")
async def process_full(
    media_id: str,
    background_tasks: BackgroundTasks,
    auto_clip: bool = True,
    db: AsyncSession = Depends(db_session_dependency),
    current_user: User = Depends(require_auth)
):
    """
    Full processing pipeline:
    1. Transcribe
    2. Analyze highlights
    3. Optionally generate clips for top highlights
    """
    user_id = current_user.id
    project = await _load_or_create_project(db, media_id, user_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Capture user_id for background task
    bg_user_id = user_id
    cache_key = _cache_key(user_id, media_id)
    
    async def _process():
        # Get a fresh database session for background task
        from models.database import get_db_session
        async for bg_db in get_db_session():
            try:
                project = projects[cache_key]
                
                # Set up progress callback for transcription service
                def update_transcription_progress(progress: float, message: str):
                    """Callback to update progress during transcription"""
                    # Transcription is 0.1 - 0.5 of total progress
                    project.progress = 0.1 + (progress * 0.4)
                    project.status_message = message
                
                # Transcribe
                project.status = ProcessingStatus.TRANSCRIBING
                project.progress = 0.05
                project.status_message = "Preparing transcription..."
                
                # Set progress callback
                transcription_service.set_progress_callback(update_transcription_progress)
                
                try:
                    transcription = await transcription_service.transcribe_with_speakers(
                        media_id=media_id,
                        file_path=Path(project.media.file_path)
                    )
                finally:
                    # Clear callback after transcription
                    transcription_service.set_progress_callback(None)
                
                project.transcription = transcription
                project.progress = 0.5
                project.status_message = "Transcription complete"
                
                # Analyze
                project.status = ProcessingStatus.ANALYZING
                project.status_message = "Analyzing content for highlights..."
                project.progress = 0.5
                
                # Calculate expected chunks for progress reporting
                total_duration = transcription.segments[-1].end if transcription.segments else 0
                chunk_duration = 600  # 10 minutes per chunk
                num_chunks = int(total_duration / chunk_duration) + 1 if total_duration > chunk_duration else 1
                
                # Track chunk progress during analysis
                # Note: highlight_detector doesn't have progress callback, so we estimate
                # We'll update status after each chunk completes (via logging)
                project.status_message = f"Analyzing {num_chunks} chunk{'s' if num_chunks > 1 else ''} for highlights..."
                
                highlights = await highlight_detector.analyze(
                    media_id=media_id,
                    transcription=transcription
                )
                project.highlights = highlights
                project.progress = 0.8
                project.status_message = f"Found {len(highlights.highlights)} highlights"
                
                # Auto-generate clips for top 3 highlights
                if auto_clip and highlights.highlights:
                    project.status_message = "Generating clips..."
                    
                    # Get existing clips for duplicate checking
                    bg_media_uuid = UUID(media_id)
                    bg_existing_clips = await clip_repository.get_by_media_id(bg_db, bg_media_uuid)
                    existing_clip_ids = {str(c.id) for c in bg_existing_clips}
                    
                    clip_count = 0
                    total_clips = min(len(highlights.highlights), 3) * 2  # 2 platforms each
                    
                    for highlight in highlights.highlights[:3]:
                        captions = [
                            seg for seg in transcription.segments
                            if seg.start >= highlight.start and seg.end <= highlight.end
                        ]
                        
                        # Generate for common platforms
                        for platform in [Platform.INSTAGRAM_REELS, Platform.TIKTOK]:
                            clip_count += 1
                            project.status_message = f"Generating clip {clip_count}/{total_clips}..."
                            project.progress = 0.8 + (0.15 * clip_count / total_clips)
                            
                            clip = await clip_generator.create_clip(
                                media=project.media,
                                start=highlight.start,
                                end=highlight.end,
                                platform=platform,
                                captions=captions,
                                title=highlight.title,
                                check_duplicates=True,
                                existing_clips=bg_existing_clips
                            )
                            # Only append if it's a new clip (not a duplicate)
                            if clip.id not in existing_clip_ids:
                                project.clips.append(clip)
                                existing_clip_ids.add(clip.id)  # Track to avoid duplicates in same batch
                
                project.status = ProcessingStatus.COMPLETE
                project.progress = 1.0
                project.status_message = "Processing complete!"
                
                # Save to database
                await _save_project(bg_db, media_id, user_id=bg_user_id)
                
            except Exception as e:
                project.status = ProcessingStatus.ERROR
                project.error = str(e)
                project.status_message = f"Error: {str(e)[:100]}"
                logger.error(f"Processing error: {e}")
                await _save_project(bg_db, media_id, user_id=bg_user_id)
    
    # Run in background
    background_tasks.add_task(asyncio.create_task, _process())
    
    return {"status": "processing", "media_id": media_id}

