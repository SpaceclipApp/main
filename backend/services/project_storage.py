"""
Project storage service for persistence
Saves projects to disk so users can resume later
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import asyncio

from config import settings
from models import ProjectState, MediaInfo, TranscriptionResult, HighlightAnalysis, ClipResult

logger = logging.getLogger(__name__)

# Storage directory
PROJECTS_DIR = settings.upload_dir / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


class ProjectStorage:
    """Handles project persistence to disk"""
    
    def __init__(self):
        self.projects_dir = PROJECTS_DIR
    
    def _get_project_path(self, media_id: str) -> Path:
        """Get path to project JSON file"""
        return self.projects_dir / f"{media_id}.json"
    
    async def save_project(self, media_id: str, state: ProjectState) -> None:
        """Save project state to disk"""
        path = self._get_project_path(media_id)
        
        def _save():
            try:
                data = {
                    "media_id": media_id,
                    "saved_at": datetime.utcnow().isoformat(),
                    "status": state.status.value if hasattr(state.status, 'value') else str(state.status),
                    "progress": state.progress or 0,
                    "error": state.error,
                    "media": state.media.model_dump() if state.media else None,
                    "transcription": state.transcription.model_dump() if state.transcription else None,
                    "highlights": state.highlights.model_dump() if state.highlights else None,
                    "clips": [clip.model_dump() for clip in state.clips] if state.clips else [],
                }
                
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                logger.info(f"Saved project {media_id}")
            except Exception as e:
                logger.error(f"Failed to save project {media_id}: {e}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)
    
    async def load_project(self, media_id: str) -> Optional[ProjectState]:
        """Load project state from disk"""
        path = self._get_project_path(media_id)
        
        if not path.exists():
            return None
        
        def _load():
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct ProjectState
            media = MediaInfo(**data["media"]) if data.get("media") else None
            
            transcription = None
            if data.get("transcription"):
                transcription = TranscriptionResult(**data["transcription"])
            
            highlights = None
            if data.get("highlights"):
                highlights = HighlightAnalysis(**data["highlights"])
            
            clips = []
            if data.get("clips"):
                clips = [ClipResult(**c) for c in data["clips"]]
            
            return ProjectState(
                media=media,
                status=data.get("status", "pending"),
                progress=data.get("progress", 0),
                error=data.get("error"),
                transcription=transcription,
                highlights=highlights,
                clips=clips,
            )
        
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, _load)
        except Exception as e:
            logger.error(f"Failed to load project {media_id}: {e}")
            return None
    
    async def list_projects(self) -> list[dict]:
        """List all saved projects"""
        def _list():
            projects = []
            for path in self.projects_dir.glob("*.json"):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    
                    if not data:
                        continue
                    
                    # Safely extract media info
                    media = data.get("media") or {}
                    highlights_data = data.get("highlights") or {}
                    
                    # Extract summary info
                    projects.append({
                        "media_id": data.get("media_id"),
                        "title": media.get("original_filename", "Untitled") if media else "Untitled",
                        "media_type": media.get("media_type", "unknown") if media else "unknown",
                        "duration": media.get("duration", 0) if media else 0,
                        "status": data.get("status", "unknown"),
                        "saved_at": data.get("saved_at"),
                        "clips_count": len(data.get("clips") or []),
                        "highlights_count": len(highlights_data.get("highlights") or []) if highlights_data else 0,
                    })
                except Exception as e:
                    logger.warning(f"Failed to read project {path}: {e}")
            
            # Sort by saved_at descending
            projects.sort(key=lambda p: p.get("saved_at") or "", reverse=True)
            return projects
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _list)
    
    async def delete_project(self, media_id: str) -> bool:
        """Delete a saved project and its associated files"""
        path = self._get_project_path(media_id)
        
        def _delete():
            deleted = False
            
            # Delete the project JSON file
            if path.exists():
                path.unlink()
                deleted = True
            
            # Delete associated media files
            from config import settings
            
            # Delete uploaded media
            for ext in ['m4a', 'mp3', 'wav', 'mp4', 'webm', 'ogg']:
                media_path = settings.upload_dir / f"{media_id}.{ext}"
                if media_path.exists():
                    media_path.unlink()
                    logger.info(f"Deleted media file: {media_path}")
            
            # Delete generated clips (all files starting with media_id)
            for clip_file in settings.output_dir.glob(f"*"):
                if str(clip_file.name).startswith(media_id[:8]):
                    clip_file.unlink()
                    logger.info(f"Deleted clip file: {clip_file}")
            
            return deleted
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _delete)
    
    def delete_project(self, media_id: str) -> bool:
        """Synchronous version of delete_project"""
        path = self._get_project_path(media_id)
        
        deleted = False
        
        # Delete the project JSON file
        if path.exists():
            path.unlink()
            deleted = True
        
        # Delete associated media files
        from config import settings
        
        # Delete uploaded media
        for ext in ['m4a', 'mp3', 'wav', 'mp4', 'webm', 'ogg']:
            media_path = settings.upload_dir / f"{media_id}.{ext}"
            if media_path.exists():
                media_path.unlink()
                logger.info(f"Deleted media file: {media_path}")
        
        return deleted
    
    def clear_project_clips(self, media_id: str) -> bool:
        """Clear all generated clips for a project"""
        from config import settings
        
        cleared = False
        
        # Load project to get clip info
        path = self._get_project_path(media_id)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Delete clip files
                clips = data.get("clips", [])
                for clip in clips:
                    clip_path = Path(clip.get("file_path", ""))
                    if clip_path.exists():
                        clip_path.unlink()
                        cleared = True
                
                # Update project to remove clips
                data["clips"] = []
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                logger.info(f"Cleared clips for project {media_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to clear clips for {media_id}: {e}")
        
        return cleared
    
    def project_exists(self, media_id: str) -> bool:
        """Check if a project exists"""
        return self._get_project_path(media_id).exists()


# Singleton instance
project_storage = ProjectStorage()

