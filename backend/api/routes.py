"""
API routes for SpaceClip
"""
import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from config import settings
from models import (
    MediaUploadRequest,
    MediaInfo,
    TranscriptionResult,
    HighlightAnalysis,
    ClipRequest,
    ClipResult,
    ProjectState,
    ProcessingStatus,
    Platform,
)
from services import (
    media_downloader,
    transcription_service,
    highlight_detector,
    clip_generator,
)
from services.project_storage import project_storage

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory project store (with disk persistence)
projects: dict[str, ProjectState] = {}


async def _save_project(media_id: str):
    """Save project to disk"""
    if media_id in projects:
        await project_storage.save_project(media_id, projects[media_id])


async def _load_or_create_project(media_id: str) -> ProjectState:
    """Load project from disk or memory"""
    if media_id in projects:
        return projects[media_id]
    
    # Try loading from disk
    loaded = await project_storage.load_project(media_id)
    if loaded:
        projects[media_id] = loaded
        return loaded
    
    return None


@router.post("/upload/file", response_model=MediaInfo)
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload a media file (video or audio)"""
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
        
        # Create project
        projects[media_info.id] = ProjectState(
            media=media_info,
            status=ProcessingStatus.PENDING
        )
        
        # Save to disk
        await _save_project(media_info.id)
        
        return media_info
        
    except Exception as e:
        # Cleanup on error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/url", response_model=MediaInfo)
async def upload_from_url(request: MediaUploadRequest):
    """Download and process media from URL (YouTube, X Spaces, etc.)"""
    try:
        media_info = await media_downloader.download(request.url)
        
        # Create project
        projects[media_info.id] = ProjectState(
            media=media_info,
            status=ProcessingStatus.PENDING
        )
        
        # Save to disk
        await _save_project(media_info.id)
        
        return media_info
        
    except Exception as e:
        logger.error(f"URL download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe/{media_id}", response_model=TranscriptionResult)
async def transcribe_media(
    media_id: str, 
    language: Optional[str] = None,
    num_speakers: Optional[int] = None
):
    """Transcribe uploaded media with speaker detection"""
    project = await _load_or_create_project(media_id)
    
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
        
        # Save to disk
        await _save_project(media_id)
        
        return result
        
    except Exception as e:
        project.status = ProcessingStatus.ERROR
        project.error = str(e)
        await _save_project(media_id)
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
    append: bool = False
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
    project = await _load_or_create_project(media_id)
    
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
        
        # Save to disk
        await _save_project(media_id)
        
        return result
        
    except Exception as e:
        project.status = ProcessingStatus.ERROR
        project.error = str(e)
        await _save_project(media_id)
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clips", response_model=list[ClipResult])
async def create_clips(request: ClipRequest):
    """Create clips for specified platforms"""
    project = await _load_or_create_project(request.media_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get captions for the clip range if requested
    captions = None
    if request.include_captions and project.transcription:
        captions = [
            seg for seg in project.transcription.segments
            if seg.start >= request.start and seg.end <= request.end
        ]
    
    try:
        results = []
        for platform in request.platforms:
            clip = await clip_generator.create_clip(
                media=project.media,
                start=request.start,
                end=request.end,
                platform=platform,
                captions=captions,
                title=request.title,
                color_scheme=request.audiogram_style or "cosmic"
            )
            results.append(clip)
            project.clips.append(clip)
        
        # Save to disk
        await _save_project(request.media_id)
        
        return results
        
    except Exception as e:
        logger.error(f"Clip creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=list[dict])
async def list_projects():
    """List all saved projects"""
    return await project_storage.list_projects()


@router.get("/projects/{media_id}", response_model=ProjectState)
async def get_project(media_id: str):
    """Get full project state"""
    project = await _load_or_create_project(media_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return project


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
async def delete_project(media_id: str):
    """Delete a project and its files"""
    if media_id not in projects:
        raise HTTPException(status_code=404, detail="Media not found")
    
    project = projects[media_id]
    
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
    
    # Remove from store
    del projects[media_id]
    
    return {"status": "deleted"}


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
    auto_clip: bool = True
):
    """
    Full processing pipeline:
    1. Transcribe
    2. Analyze highlights
    3. Optionally generate clips for top highlights
    """
    if media_id not in projects:
        raise HTTPException(status_code=404, detail="Media not found")
    
    async def _process():
        project = projects[media_id]
        
        try:
            # Transcribe
            project.status = ProcessingStatus.TRANSCRIBING
            project.progress = 0.2
            
            transcription = await transcription_service.transcribe_with_speakers(
                media_id=media_id,
                file_path=Path(project.media.file_path)
            )
            project.transcription = transcription
            project.progress = 0.5
            
            # Analyze
            project.status = ProcessingStatus.ANALYZING
            highlights = await highlight_detector.analyze(
                media_id=media_id,
                transcription=transcription
            )
            project.highlights = highlights
            project.progress = 0.8
            
            # Auto-generate clips for top 3 highlights
            if auto_clip and highlights.highlights:
                for highlight in highlights.highlights[:3]:
                    captions = [
                        seg for seg in transcription.segments
                        if seg.start >= highlight.start and seg.end <= highlight.end
                    ]
                    
                    # Generate for common platforms
                    for platform in [Platform.INSTAGRAM_REELS, Platform.TIKTOK]:
                        clip = await clip_generator.create_clip(
                            media=project.media,
                            start=highlight.start,
                            end=highlight.end,
                            platform=platform,
                            captions=captions,
                            title=highlight.title
                        )
                        project.clips.append(clip)
            
            project.status = ProcessingStatus.COMPLETE
            project.progress = 1.0
            
        except Exception as e:
            project.status = ProcessingStatus.ERROR
            project.error = str(e)
            logger.error(f"Processing error: {e}")
    
    # Run in background
    background_tasks.add_task(asyncio.create_task, _process())
    
    return {"status": "processing", "media_id": media_id}

