"""
Media downloading service for YouTube, X Spaces, and other URLs
"""
import asyncio
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional
import yt_dlp
import logging

from config import settings
from models import MediaType, SourceType, MediaInfo

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Downloads media from various sources"""
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
    
    def detect_source_type(self, url: str) -> SourceType:
        """Detect the source type from URL"""
        url_lower = url.lower()
        
        # YouTube
        if any(domain in url_lower for domain in ['youtube.com', 'youtu.be']):
            return SourceType.YOUTUBE
        
        # X/Twitter Spaces
        if 'twitter.com/i/spaces' in url_lower or 'x.com/i/spaces' in url_lower:
            return SourceType.X_SPACE
        
        # Generic URL
        return SourceType.URL
    
    async def download_youtube(self, url: str) -> MediaInfo:
        """Download video/audio from YouTube"""
        media_id = str(uuid.uuid4())
        output_path = self.upload_dir / f"{media_id}.mp4"
        
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'outtmpl': str(output_path),
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download)
        
        duration = info.get('duration', 0)
        title = info.get('title', 'Untitled')
        
        # Generate thumbnail
        thumbnail_path = await self._generate_thumbnail(output_path, media_id)
        
        return MediaInfo(
            id=media_id,
            filename=f"{media_id}.mp4",
            original_filename=title,
            media_type=MediaType.VIDEO,
            source_type=SourceType.YOUTUBE,
            source_url=url,  # Save original YouTube URL
            duration=duration,
            file_path=str(output_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        )
    
    async def download_x_space(self, url: str) -> MediaInfo:
        """Download audio from X/Twitter Space"""
        media_id = str(uuid.uuid4())
        output_path = self.upload_dir / f"{media_id}.m4a"
        
        # X Spaces uses HLS streaming, yt-dlp can handle it
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.upload_dir / f"{media_id}"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'quiet': True,
            'no_warnings': True,
            # May need cookies for some spaces
            'cookiesfrombrowser': ('chrome',),  # Try to use Chrome cookies
        }
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, _download)
            
            duration = info.get('duration', 0)
            title = info.get('title', 'X Space')
            
            return MediaInfo(
                id=media_id,
                filename=f"{media_id}.m4a",
                original_filename=title,
                media_type=MediaType.AUDIO,
                source_type=SourceType.X_SPACE,
                duration=duration,
                file_path=str(output_path),
            )
        except Exception as e:
            logger.error(f"Failed to download X Space: {e}")
            # Try alternative method using direct M3U8 extraction
            return await self._download_x_space_fallback(url, media_id)
    
    async def _download_x_space_fallback(self, url: str, media_id: str) -> MediaInfo:
        """Fallback method for X Space download using direct approach"""
        import requests
        
        # Extract space ID from URL
        space_id_match = re.search(r'/spaces/(\w+)', url)
        if not space_id_match:
            raise ValueError("Could not extract Space ID from URL")
        
        space_id = space_id_match.group(1)
        output_path = self.upload_dir / f"{media_id}.m4a"
        
        # This is a simplified approach - production would need proper Twitter API
        # For now, we'll use yt-dlp with different options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.upload_dir / f"{media_id}.%(ext)s"),
            'quiet': True,
        }
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download)
        
        # Find the actual output file
        for ext in ['m4a', 'mp3', 'aac', 'opus', 'webm']:
            potential_path = self.upload_dir / f"{media_id}.{ext}"
            if potential_path.exists():
                output_path = potential_path
                break
        
        return MediaInfo(
            id=media_id,
            filename=output_path.name,
            original_filename=info.get('title', 'X Space'),
            media_type=MediaType.AUDIO,
            source_type=SourceType.X_SPACE,
            duration=info.get('duration', 0),
            file_path=str(output_path),
        )
    
    async def download_generic_url(self, url: str) -> MediaInfo:
        """Download media from generic URL"""
        media_id = str(uuid.uuid4())
        
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': str(self.upload_dir / f"{media_id}.%(ext)s"),
            'quiet': True,
        }
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download)
        
        # Determine media type and find output file
        ext = info.get('ext', 'mp4')
        output_path = self.upload_dir / f"{media_id}.{ext}"
        
        # Check if it's audio or video
        if info.get('vcodec') == 'none' or ext in ['mp3', 'm4a', 'aac', 'opus', 'wav']:
            media_type = MediaType.AUDIO
        else:
            media_type = MediaType.VIDEO
        
        thumbnail_path = None
        if media_type == MediaType.VIDEO:
            thumbnail_path = await self._generate_thumbnail(output_path, media_id)
        
        return MediaInfo(
            id=media_id,
            filename=f"{media_id}.{ext}",
            original_filename=info.get('title', 'Media'),
            media_type=media_type,
            source_type=SourceType.URL,
            duration=info.get('duration', 0),
            file_path=str(output_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        )
    
    async def process_upload(
        self, 
        file_path: Path, 
        original_filename: str
    ) -> MediaInfo:
        """Process an uploaded file"""
        media_id = str(uuid.uuid4())
        ext = file_path.suffix.lower()
        
        # Determine media type
        audio_exts = {'.mp3', '.m4a', '.aac', '.wav', '.ogg', '.opus', '.flac'}
        media_type = MediaType.AUDIO if ext in audio_exts else MediaType.VIDEO
        
        # Move to uploads directory with new name
        new_path = self.upload_dir / f"{media_id}{ext}"
        file_path.rename(new_path)
        
        # Get duration using ffprobe
        duration = await self._get_duration(new_path)
        
        # Generate thumbnail for video
        thumbnail_path = None
        if media_type == MediaType.VIDEO:
            thumbnail_path = await self._generate_thumbnail(new_path, media_id)
        
        return MediaInfo(
            id=media_id,
            filename=f"{media_id}{ext}",
            original_filename=original_filename,
            media_type=media_type,
            source_type=SourceType.UPLOAD,
            duration=duration,
            file_path=str(new_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        )
    
    async def _get_duration(self, file_path: Path) -> float:
        """Get media duration using ffprobe"""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)
        ]
        
        def _run():
            result = subprocess.run(cmd, capture_output=True, text=True)
            try:
                return float(result.stdout.strip())
            except (ValueError, AttributeError):
                return 0.0
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)
    
    async def _generate_thumbnail(
        self, 
        video_path: Path, 
        media_id: str
    ) -> Optional[Path]:
        """Generate thumbnail from video"""
        thumbnail_path = self.upload_dir / f"{media_id}_thumb.jpg"
        
        cmd = [
            'ffmpeg', '-y', '-i', str(video_path),
            '-ss', '00:00:01', '-vframes', '1',
            '-vf', 'scale=320:-1',
            str(thumbnail_path)
        ]
        
        def _run():
            subprocess.run(cmd, capture_output=True)
            return thumbnail_path if thumbnail_path.exists() else None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)
    
    async def download(self, url: str) -> MediaInfo:
        """Download media from URL, auto-detecting source type"""
        source_type = self.detect_source_type(url)
        
        if source_type == SourceType.YOUTUBE:
            return await self.download_youtube(url)
        elif source_type == SourceType.X_SPACE:
            return await self.download_x_space(url)
        else:
            return await self.download_generic_url(url)


# Singleton instance
media_downloader = MediaDownloader()


