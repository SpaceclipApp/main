"""
Clip and audiogram generation service using FFmpeg
"""
import asyncio
import hashlib
import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional
import math

from config import settings
from models import (
    MediaInfo, 
    MediaType,
    Platform, 
    PlatformSpec, 
    PLATFORM_SPECS,
    TranscriptSegment,
    ClipResult
)
from services.audiogram_generator import audiogram_generator, AudiogramConfig

logger = logging.getLogger(__name__)


class ClipGenerator:
    """Generates video clips and audiograms"""
    
    def __init__(self):
        self.output_dir = settings.output_dir
        
        # Audiogram color schemes
        self.color_schemes = {
            'cosmic': {
                'background': '#0f0a1f',  # Synced with audiogram_generator
                'waveform': '#a855f7',  # Synced with audiogram_generator
                'waveform_gradient': '#a855f7',
                'text': '#ffffff',
                'accent': '#06b6d4'
            },
            'minimal': {
                'background': '#ffffff',
                'waveform': '#333333',  # Synced with audiogram_generator
                'text': '#000000',
                'accent': '#666666'
            },
            'neon': {
                'background': '#000000',
                'waveform': '#00ffff',  # Synced with audiogram_generator
                'waveform_gradient': '#00ffff',
                'text': '#ffffff',
                'accent': '#ff00ff'
            },
            'sunset': {
                'background': '#1a1a2e',
                'waveform': '#ff6b6b',  # Synced with audiogram_generator
                'waveform_gradient': '#ff6b6b',
                'text': '#ffffff',
                'accent': '#ffd93d'
            }
        }
    
    def _generate_clip_hash(
        self,
        media_id: str,
        start: float,
        end: float,
        platform: Platform,
        captions_text: Optional[str] = None
    ) -> str:
        """
        Generate a deterministic hash for a clip based on its content.
        Used to prevent duplicate clips on reanalysis.
        
        Args:
            media_id: Media item ID
            start: Clip start time
            end: Clip end time
            platform: Target platform
            captions_text: Optional text content for hashing
            
        Returns:
            Deterministic UUID string based on content hash
        """
        # Round start/end to 2 decimal places to handle floating point precision
        start_rounded = round(start, 2)
        end_rounded = round(end, 2)
        
        # Create hash input from clip characteristics
        hash_input = f"{media_id}:{start_rounded}:{end_rounded}:{platform.value}"
        if captions_text:
            # Include first 100 chars of captions text for uniqueness
            hash_input += f":{captions_text[:100]}"
        
        # Generate SHA256 hash
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        
        # Convert to UUID (use first 16 bytes)
        clip_uuid = uuid.UUID(bytes=hash_bytes[:16])
        return str(clip_uuid)
    
    def _get_captions_text(self, captions: Optional[list[TranscriptSegment]]) -> Optional[str]:
        """Extract text content from captions for hashing"""
        if not captions:
            return None
        return " ".join(seg.text.strip() for seg in captions if seg.text)
    
    async def create_clip(
        self,
        media: MediaInfo,
        start: float,
        end: float,
        platform: Platform,
        captions: Optional[list[TranscriptSegment]] = None,
        title: Optional[str] = None,
        color_scheme: str = 'cosmic',
        check_duplicates: bool = True,
        db: Optional[object] = None,
        existing_clips: Optional[list] = None
    ) -> ClipResult:
        """
        Create a platform-optimized clip
        
        For video: Extract and resize
        For audio: Create audiogram with waveform visualization
        
        Args:
            check_duplicates: If True, check for existing clips with same content
            db: Optional database session for duplicate checking
            existing_clips: Optional list of existing clips to check against
        """
        # Generate deterministic clip ID based on content hash
        captions_text = self._get_captions_text(captions)
        clip_id = self._generate_clip_hash(
            media.id,
            start,
            end,
            platform,
            captions_text
        )
        
        # Check for duplicates if requested
        if check_duplicates and existing_clips:
            # Check if a clip with this ID already exists
            for existing in existing_clips:
                if str(existing.id) == clip_id:
                    logger.info(f"Duplicate clip detected, returning existing: {clip_id}")
                    # Return existing clip as ClipResult
                    return ClipResult(
                        id=str(existing.id),
                        media_id=str(existing.media_id),
                        platform=Platform(existing.platform),
                        file_path=existing.file_path,
                        duration=existing.duration,
                        width=existing.width,
                        height=existing.height,
                        has_captions=existing.has_captions,
                    )
        
        spec = PLATFORM_SPECS[platform]
        
        if media.media_type == MediaType.VIDEO:
            output_path = await self._create_video_clip(
                clip_id, media, start, end, spec, captions
            )
        else:
            output_path = await self._create_audiogram(
                clip_id, media, start, end, spec, captions, title, color_scheme
            )
        
        return ClipResult(
            id=clip_id,
            media_id=media.id,
            platform=platform,
            file_path=str(output_path),
            duration=end - start,
            width=spec.width,
            height=spec.height,
            has_captions=captions is not None and len(captions) > 0
        )
    
    async def _create_video_clip(
        self,
        clip_id: str,
        media: MediaInfo,
        start: float,
        end: float,
        spec: PlatformSpec,
        captions: Optional[list[TranscriptSegment]] = None
    ) -> Path:
        """Create video clip with optional captions"""
        output_path = self.output_dir / f"{clip_id}.mp4"
        duration = end - start
        
        # Build filter chain
        filters = []
        
        # Scale and crop to target aspect ratio
        if spec.aspect_ratio == "9:16":
            # Portrait - crop from center if landscape
            filters.append(
                f"scale={spec.width}:{spec.height}:force_original_aspect_ratio=increase,"
                f"crop={spec.width}:{spec.height}"
            )
        elif spec.aspect_ratio == "1:1":
            # Square - crop to center
            filters.append(
                f"scale={max(spec.width, spec.height)}:{max(spec.width, spec.height)}:force_original_aspect_ratio=increase,"
                f"crop={spec.width}:{spec.height}"
            )
        else:
            # Landscape - standard scale
            filters.append(
                f"scale={spec.width}:{spec.height}:force_original_aspect_ratio=decrease,"
                f"pad={spec.width}:{spec.height}:(ow-iw)/2:(oh-ih)/2"
            )
        
        # Add captions as subtitles
        if captions:
            srt_path = await self._create_srt_file(clip_id, captions, start)
            filters.append(
                f"subtitles={srt_path}:force_style='FontSize=24,FontName=Arial,PrimaryColour=&HFFFFFF&,"
                f"OutlineColour=&H000000&,Outline=2,Shadow=1,MarginV=30'"
            )
        
        filter_chain = ",".join(filters)
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', media.file_path,
            '-t', str(duration),
            '-vf', filter_chain,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        await self._run_ffmpeg(cmd)
        return output_path
    
    async def _create_audiogram(
        self,
        clip_id: str,
        media: MediaInfo,
        start: float,
        end: float,
        spec: PlatformSpec,
        captions: Optional[list[TranscriptSegment]] = None,
        title: Optional[str] = None,
        color_scheme: str = 'cosmic'
    ) -> Path:
        """Create audiogram using the new improved audiogram generator"""
        # Use the new audiogram generator for better quality output
        return await audiogram_generator.create_audiogram(
            clip_id=clip_id,
            media=media,
            start=start,
            end=end,
            spec=spec,
            captions=captions,
            title=title or media.original_filename or "Audio Clip",
            theme=color_scheme
        )
    
    async def _create_audiogram_legacy(
        self,
        clip_id: str,
        media: MediaInfo,
        start: float,
        end: float,
        spec: PlatformSpec,
        captions: Optional[list[TranscriptSegment]] = None,
        title: Optional[str] = None,
        color_scheme: str = 'cosmic'
    ) -> Path:
        """Legacy audiogram creation - kept for reference"""
        output_path = self.output_dir / f"{clip_id}.mp4"
        duration = end - start
        colors = self.color_schemes.get(color_scheme, self.color_schemes['cosmic'])
        
        # Calculate layout
        waveform_height = int(spec.height * 0.25)  # 25% of height
        waveform_y = int(spec.height * 0.45)  # Center position
        title_y = int(spec.height * 0.08)  # Title near top
        timecode_y = int(spec.height * 0.75)  # Timecode below waveform
        caption_margin = int(spec.height * 0.12)  # Caption margin from bottom
        
        # Build complex filter
        filters = []
        
        # Create background with gradient
        bg_filter = (
            f"color=c={colors['background']}:s={spec.width}x{spec.height}:"
            f"d={duration}:r=30[bg]"
        )
        filters.append(bg_filter)
        
        # Audio visualization - animated bars
        audio_filter = (
            f"[0:a]showwaves=s={spec.width}x{waveform_height}:"
            f"mode=p2p:rate=30:colors={colors['waveform']}|{colors.get('waveform_gradient', colors['waveform'])}[waves]"
        )
        filters.append(audio_filter)
        
        # Overlay waveform on background
        overlay_filter = f"[bg][waves]overlay=0:{waveform_y}[v1]"
        filters.append(overlay_filter)
        
        current_output = "[v1]"
        filter_idx = 2
        
        # Add title text
        display_title = title or media.original_filename or "Audio Clip"
        # Truncate if too long
        if len(display_title) > 50:
            display_title = display_title[:47] + "..."
        # Escape special characters for FFmpeg drawtext
        safe_title = display_title.replace("'", r"'\\''").replace(":", r"\:").replace("\\", r"\\\\")
        
        title_filter = (
            f"{current_output}drawtext=text='{safe_title}':"
            f"fontfile=/System/Library/Fonts/Helvetica.ttc:"
            f"fontsize={int(spec.height * 0.045)}:"
            f"fontcolor={colors['text']}:"
            f"x=(w-text_w)/2:y={title_y}[v{filter_idx}]"
        )
        filters.append(title_filter)
        current_output = f"[v{filter_idx}]"
        filter_idx += 1
        
        # Add timecode display (shows current position)
        timecode_filter = (
            f"{current_output}drawtext=text='%{{pts\\:hms}}':"
            f"fontfile=/System/Library/Fonts/Courier.dfont:"
            f"fontsize={int(spec.height * 0.03)}:"
            f"fontcolor={colors['accent']}:"
            f"x=(w-text_w)/2:y={timecode_y}[v{filter_idx}]"
        )
        filters.append(timecode_filter)
        current_output = f"[v{filter_idx}]"
        filter_idx += 1
        
        # Add branding watermark
        brand_filter = (
            f"{current_output}drawtext=text='SpaceClip':"
            f"fontfile=/System/Library/Fonts/Helvetica.ttc:"
            f"fontsize={int(spec.height * 0.02)}:"
            f"fontcolor={colors['text']}@0.5:"
            f"x=w-text_w-20:y=h-text_h-20[v{filter_idx}]"
        )
        filters.append(brand_filter)
        current_output = f"[v{filter_idx}]"
        filter_idx += 1
        
        # Add captions (subtitles) if provided
        if captions and len(captions) > 0:
            # Create subtitle file
            srt_path = await self._create_srt_file(clip_id, captions, start)
            
            # Add subtitles with styling
            sub_filter = (
                f"{current_output}subtitles={srt_path}:"
                f"force_style='FontSize={int(spec.height * 0.038)},"
                f"FontName=Arial,PrimaryColour=&HFFFFFF&,"
                f"OutlineColour=&H000000&,Outline=2,"
                f"Shadow=1,Alignment=2,MarginV={caption_margin}'[vout]"
            )
            filters.append(sub_filter)
            current_output = "[vout]"
        
        filter_complex = ";".join(filters)
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', media.file_path,
            '-t', str(duration),
            '-filter_complex', filter_complex,
            '-map', current_output,
            '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-r', '30',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        await self._run_ffmpeg(cmd)
        return output_path
    
    async def _create_advanced_audiogram(
        self,
        clip_id: str,
        media: MediaInfo,
        start: float,
        end: float,
        spec: PlatformSpec,
        captions: Optional[list[TranscriptSegment]] = None,
        title: Optional[str] = None,
        color_scheme: str = 'cosmic'
    ) -> Path:
        """
        Create advanced audiogram with circular/spectrum visualization
        This is more visually appealing but requires more processing
        """
        output_path = self.output_dir / f"{clip_id}.mp4"
        duration = end - start
        colors = self.color_schemes.get(color_scheme, self.color_schemes['cosmic'])
        
        # Create temp audio extract
        temp_audio = self.output_dir / f"{clip_id}_temp.wav"
        
        extract_cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', media.file_path,
            '-t', str(duration),
            '-vn', '-acodec', 'pcm_s16le',
            str(temp_audio)
        ]
        await self._run_ffmpeg(extract_cmd)
        
        # Create visualization with showcqt (spectrum) or avectorscope
        filter_complex = (
            f"[0:a]showcqt=s={spec.width}x{int(spec.height * 0.4)}:"
            f"bar_g=2:sono_g=4:bar_v=9:sono_v=13:"
            f"fontcolor={colors['text']}[spectrum];"
            f"color=c={colors['background']}:s={spec.width}x{spec.height}:"
            f"d={duration}[bg];"
            f"[bg][spectrum]overlay=0:{int(spec.height * 0.35)}[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(temp_audio),
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-r', '30',
            '-t', str(duration),
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        await self._run_ffmpeg(cmd)
        
        # Cleanup temp file
        if temp_audio.exists():
            temp_audio.unlink()
        
        return output_path
    
    async def _create_srt_file(
        self,
        clip_id: str,
        captions: list[TranscriptSegment],
        offset: float
    ) -> Path:
        """Create SRT subtitle file"""
        srt_path = self.output_dir / f"{clip_id}.srt"
        
        lines = []
        for i, seg in enumerate(captions, 1):
            # Adjust times relative to clip start
            start = seg.start - offset
            end = seg.end - offset
            
            if start < 0:
                start = 0
            
            start_str = self._format_srt_time(start)
            end_str = self._format_srt_time(end)
            
            lines.append(str(i))
            lines.append(f"{start_str} --> {end_str}")
            lines.append(seg.text)
            lines.append("")
        
        srt_path.write_text("\n".join(lines))
        return srt_path
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    async def _run_ffmpeg(self, cmd: list[str]) -> None:
        """Run FFmpeg command"""
        def _run():
            logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")
            return result
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run)
    
    async def create_batch_clips(
        self,
        media: MediaInfo,
        clips: list[dict],
        platforms: list[Platform],
        captions_map: dict[str, list[TranscriptSegment]] = None
    ) -> list[ClipResult]:
        """
        Create multiple clips for multiple platforms
        
        Args:
            media: Source media
            clips: List of clip definitions [{"start": float, "end": float, "title": str}]
            platforms: Target platforms
            captions_map: Optional map of highlight_id to captions
        """
        results = []
        
        for clip in clips:
            for platform in platforms:
                captions = None
                if captions_map and clip.get('id') in captions_map:
                    captions = captions_map[clip['id']]
                
                result = await self.create_clip(
                    media=media,
                    start=clip['start'],
                    end=clip['end'],
                    platform=platform,
                    captions=captions,
                    title=clip.get('title')
                )
                results.append(result)
        
        return results


# Singleton instance
clip_generator = ClipGenerator()


