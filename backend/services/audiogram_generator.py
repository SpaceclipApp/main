"""
Professional audiogram generation with customizable branding
"""
import asyncio
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from config import settings
from models import MediaInfo, TranscriptSegment, PlatformSpec

logger = logging.getLogger(__name__)


@dataclass
class AudiogramConfig:
    """Configuration for audiogram generation"""
    background_color: str = "#0f0a1f"
    accent_color: str = "#7c3aed"
    text_color: str = "#ffffff"
    waveform_color: str = "#a855f7"
    highlight_color: str = "#06b6d4"


class AudiogramGenerator:
    """Generates professional audiograms"""
    
    def __init__(self):
        self.output_dir = settings.output_dir
        self.temp_dir = settings.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Predefined themes
        self.themes = {
            "cosmic": AudiogramConfig(
                background_color="#0f0a1f",
                accent_color="#7c3aed",
                text_color="#ffffff",
                waveform_color="#a855f7",
                highlight_color="#06b6d4",
            ),
            "neon": AudiogramConfig(
                background_color="#000000",
                accent_color="#00ff88",
                text_color="#ffffff",
                waveform_color="#00ffff",
                highlight_color="#ff00ff",
            ),
            "sunset": AudiogramConfig(
                background_color="#1a1a2e",
                accent_color="#e94560",
                text_color="#ffffff",
                waveform_color="#ff6b6b",
                highlight_color="#ffd93d",
            ),
            "minimal": AudiogramConfig(
                background_color="#ffffff",
                accent_color="#000000",
                text_color="#000000",
                waveform_color="#333333",
                highlight_color="#0066ff",
            ),
        }
    
    async def create_audiogram(
        self,
        clip_id: str,
        media: MediaInfo,
        start: float,
        end: float,
        spec: PlatformSpec,
        captions: Optional[List[TranscriptSegment]] = None,
        title: Optional[str] = None,
        speaker_name: Optional[str] = None,
        theme: str = "cosmic",
        config: Optional[AudiogramConfig] = None,
    ) -> Path:
        """Create a professional audiogram"""
        output_path = self.output_dir / f"{clip_id}.mp4"
        duration = end - start
        
        # Get theme config
        cfg = config if config else self.themes.get(theme, self.themes["cosmic"])
        
        # Determine layout based on aspect ratio
        is_portrait = spec.height > spec.width
        
        # Calculate dimensions
        if is_portrait:
            wf_width = int(spec.width * 0.85)
            wf_height = int(spec.height * 0.12)
            wf_x = int((spec.width - wf_width) / 2)
            wf_y = int(spec.height * 0.50)
            title_y = int(spec.height * 0.12)
            title_size = int(spec.width * 0.05)
            bar_y = int(spec.height * 0.65)
        else:
            wf_width = int(spec.width * 0.7)
            wf_height = int(spec.height * 0.15)
            wf_x = int((spec.width - wf_width) / 2)
            wf_y = int(spec.height * 0.45)
            title_y = int(spec.height * 0.10)
            title_size = int(spec.height * 0.055)
            bar_y = int(spec.height * 0.62)
        
        bar_margin = int(spec.width * 0.075)
        bar_width = spec.width - (bar_margin * 2)
        bar_height = 4
        brand_size = int(min(spec.width, spec.height) * 0.022)
        
        # Prepare title
        display_title = title or media.original_filename or "Audio Clip"
        max_chars = 40 if is_portrait else 55
        if len(display_title) > max_chars:
            display_title = display_title[:max_chars-3] + "..."
        safe_title = self._escape_text(display_title)
        
        # Build filter graph step by step
        # Step 1: Background
        filter_parts = [
            f"color=c={cfg.background_color}:s={spec.width}x{spec.height}:d={duration}:r=30[bg]"
        ]
        
        # Step 2: Waveform
        filter_parts.append(
            f"[0:a]showwaves=s={wf_width}x{wf_height}:mode=cline:rate=30:colors={cfg.waveform_color}:scale=cbrt[waves]"
        )
        
        # Step 3: Overlay waveform on background
        filter_parts.append(
            f"[bg][waves]overlay={wf_x}:{wf_y}[v1]"
        )
        
        # Step 4: Progress bar background + animated progress
        filter_parts.append(
            f"[v1]drawbox=x={bar_margin}:y={bar_y}:w={bar_width}:h={bar_height}:color={cfg.text_color}@0.2:t=fill,"
            f"drawbox=x={bar_margin}:y={bar_y}:w='min({bar_width}*t/{duration},{bar_width})':h={bar_height}:color={cfg.accent_color}:t=fill[v2]"
        )
        
        # Step 5: Title
        filter_parts.append(
            f"[v2]drawtext=text='{safe_title}':"
            f"fontfile=/System/Library/Fonts/Helvetica.ttc:"
            f"fontsize={title_size}:"
            f"fontcolor={cfg.text_color}:"
            f"x=(w-text_w)/2:y={title_y}[v3]"
        )
        
        # Step 6: Branding
        filter_parts.append(
            f"[v3]drawtext=text='SpaceClip':"
            f"fontfile=/System/Library/Fonts/Helvetica.ttc:"
            f"fontsize={brand_size}:"
            f"fontcolor={cfg.text_color}@0.4:"
            f"x=w-text_w-20:y=h-text_h-20[vout]"
        )
        
        filter_complex = ";".join(filter_parts)
        
        # Create base audiogram without captions
        temp_output = self.temp_dir / f"{clip_id}_temp.mp4" if captions else output_path
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', media.file_path,
            '-t', str(duration),
            '-filter_complex', filter_complex,
            '-map', '[vout]',
            '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-r', '30',
            '-movflags', '+faststart',
            str(temp_output)
        ]
        
        await self._run_ffmpeg(cmd)
        
        # Add captions if provided
        if captions and len(captions) > 0:
            await self._add_captions(
                temp_output, output_path, captions, start, spec, cfg, is_portrait
            )
            # Clean up temp file
            if temp_output.exists():
                temp_output.unlink()
        
        return output_path
    
    async def _add_captions(
        self,
        input_path: Path,
        output_path: Path,
        captions: List[TranscriptSegment],
        offset: float,
        spec: PlatformSpec,
        cfg: AudiogramConfig,
        is_portrait: bool
    ) -> None:
        """Add captions using SRT subtitles"""
        # Create SRT file
        srt_path = self.temp_dir / f"{output_path.stem}.srt"
        
        srt_lines = []
        for i, seg in enumerate(captions, 1):
            start_time = max(0, seg.start - offset)
            end_time = seg.end - offset
            
            if end_time <= 0:
                continue
            
            start_srt = self._seconds_to_srt(start_time)
            end_srt = self._seconds_to_srt(end_time)
            
            text = seg.text.strip()
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_srt} --> {end_srt}")
            srt_lines.append(text)
            srt_lines.append("")
        
        srt_path.write_text("\n".join(srt_lines))
        
        # Calculate subtitle size and margin
        if is_portrait:
            font_size = int(spec.width * 0.055)
            margin_v = int(spec.height * 0.18)
        else:
            font_size = int(spec.height * 0.06)
            margin_v = int(spec.height * 0.22)
        
        # Burn in subtitles
        subtitle_filter = (
            f"subtitles={srt_path}:force_style='"
            f"FontSize={font_size},FontName=Arial,"
            f"PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
            f"Outline=2,Shadow=1,Alignment=2,MarginV={margin_v}'"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-vf', subtitle_filter,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        await self._run_ffmpeg(cmd)
        
        # Clean up SRT file
        if srt_path.exists():
            srt_path.unlink()
    
    def _seconds_to_srt(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _escape_text(self, text: str) -> str:
        """Escape text for FFmpeg drawtext filter"""
        text = text.replace("\\", "\\\\\\\\")
        text = text.replace("'", "'\\''")
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text
    
    async def _run_ffmpeg(self, cmd: List[str]) -> None:
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


# Singleton
audiogram_generator = AudiogramGenerator()
