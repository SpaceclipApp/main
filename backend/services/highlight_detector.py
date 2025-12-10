"""
AI-powered highlight detection using Ollama (local LLM)
Analyzes content in chunks to ensure full coverage
"""
import asyncio
import json
import logging
import uuid
from typing import Optional
import ollama

from config import settings
from models import TranscriptionResult, Highlight, HighlightAnalysis

logger = logging.getLogger(__name__)

# Chunk size for analysis (in seconds)
CHUNK_DURATION = 600  # 10 minutes per chunk
CHUNK_OVERLAP = 30    # 30 second overlap between chunks


class HighlightDetector:
    """Detects highlights and suggests clips using local LLM"""
    
    def __init__(self):
        self.model = settings.ollama_model
        self.host = settings.ollama_host
    
    async def analyze(
        self, 
        media_id: str,
        transcription: TranscriptionResult,
        max_highlights: int = 10,
        min_clip_duration: float = 15.0,
        max_clip_duration: float = 90.0,
        time_range: Optional[tuple[float, float]] = None,
    ) -> HighlightAnalysis:
        """
        Analyze transcription and detect highlights across the FULL content
        
        Args:
            media_id: Media identifier
            transcription: Full transcription result
            max_highlights: Maximum number of highlights to return
            min_clip_duration: Minimum clip duration in seconds
            max_clip_duration: Maximum clip duration in seconds
            time_range: Optional (start, end) to analyze specific portion
        
        Returns:
            HighlightAnalysis with detected highlights from entire content
        """
        logger.info(f"Analyzing highlights for {media_id}")
        
        # Get total duration
        if not transcription.segments:
            return HighlightAnalysis(media_id=media_id, highlights=[])
        
        total_duration = transcription.segments[-1].end
        
        # Apply time range filter if specified
        if time_range:
            start_time, end_time = time_range
        else:
            start_time, end_time = 0, total_duration
        
        # Split into chunks for analysis
        chunks = self._create_chunks(transcription, start_time, end_time)
        logger.info(f"Analyzing {len(chunks)} chunks covering {end_time - start_time:.0f}s")
        
        # Calculate highlights per chunk to ensure even distribution
        highlights_per_chunk = max(2, max_highlights // len(chunks) + 1)
        
        # Analyze each chunk
        all_highlights = []
        for i, chunk in enumerate(chunks):
            chunk_highlights = await self._analyze_chunk(
                chunk,
                highlights_per_chunk,
                min_clip_duration,
                max_clip_duration,
                chunk_index=i,
                total_chunks=len(chunks)
            )
            all_highlights.extend(chunk_highlights)
        
        # Deduplicate overlapping highlights
        all_highlights = self._deduplicate_highlights(all_highlights)
        
        # Sort by score and limit
        all_highlights.sort(key=lambda h: h.score, reverse=True)
        final_highlights = all_highlights[:max_highlights]
        
        # Re-sort by time for better UX
        final_highlights.sort(key=lambda h: h.start)
        
        # Assign final transcript segment IDs
        for highlight in final_highlights:
            highlight.transcript_segment_ids = [
                seg.id for seg in transcription.segments
                if seg.start >= highlight.start and seg.end <= highlight.end
            ]
        
        logger.info(f"Found {len(final_highlights)} highlights across full {total_duration:.0f}s content")
        
        return HighlightAnalysis(
            media_id=media_id,
            highlights=final_highlights
        )
    
    def _create_chunks(
        self,
        transcription: TranscriptionResult,
        start_time: float,
        end_time: float
    ) -> list[dict]:
        """Split transcription into overlapping chunks for analysis"""
        chunks = []
        current_start = start_time
        
        while current_start < end_time:
            chunk_end = min(current_start + CHUNK_DURATION, end_time)
            
            # Get segments in this chunk
            chunk_segments = [
                seg for seg in transcription.segments
                if seg.start >= current_start - CHUNK_OVERLAP and seg.end <= chunk_end + CHUNK_OVERLAP
            ]
            
            if chunk_segments:
                chunks.append({
                    "start": current_start,
                    "end": chunk_end,
                    "segments": chunk_segments
                })
            
            current_start = chunk_end - CHUNK_OVERLAP  # Overlap with next chunk
            
            # Prevent infinite loop
            if current_start >= end_time - CHUNK_OVERLAP:
                break
        
        return chunks
    
    async def _analyze_chunk(
        self,
        chunk: dict,
        max_highlights: int,
        min_clip_duration: float,
        max_clip_duration: float,
        chunk_index: int,
        total_chunks: int
    ) -> list[Highlight]:
        """Analyze a single chunk of the transcript"""
        
        # Format chunk transcript
        transcript_text = self._format_chunk_for_analysis(chunk["segments"])
        
        if not transcript_text.strip():
            return []
        
        # Create prompt
        prompt = self._create_analysis_prompt(
            transcript_text,
            max_highlights,
            min_clip_duration,
            max_clip_duration,
            chunk_info=f"This is part {chunk_index + 1} of {total_chunks} of the content."
        )
        
        # Call Ollama
        def _analyze():
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'system',
                            'content': self._get_system_prompt()
                        },
                        {
                            'role': 'user', 
                            'content': prompt
                        }
                    ],
                    options={
                        'temperature': 0.3,
                        'num_ctx': 8192,  # Larger context window
                    }
                )
                return response['message']['content']
            except Exception as e:
                logger.error(f"Ollama error for chunk {chunk_index}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _analyze)
        
        if not response:
            # Fallback for this chunk
            return self._fallback_chunk_highlights(chunk, max_highlights)
        
        # Parse response
        highlights = self._parse_highlights(
            response,
            chunk["segments"],
            min_clip_duration,
            max_clip_duration
        )
        
        return highlights
    
    def _format_chunk_for_analysis(self, segments: list) -> str:
        """Format chunk segments for LLM analysis"""
        lines = []
        for seg in segments:
            timestamp = f"[{self._format_time(seg.start)} - {self._format_time(seg.end)}]"
            speaker = f"{seg.speaker}: " if seg.speaker else ""
            lines.append(f"{timestamp} {speaker}{seg.text}")
        return "\n".join(lines)
    
    def _deduplicate_highlights(self, highlights: list[Highlight]) -> list[Highlight]:
        """Remove overlapping highlights, keeping higher-scored ones"""
        if not highlights:
            return []
        
        # Sort by score descending
        highlights.sort(key=lambda h: h.score, reverse=True)
        
        kept = []
        for highlight in highlights:
            # Check if this overlaps significantly with any kept highlight
            dominated = False
            for kept_h in kept:
                overlap_start = max(highlight.start, kept_h.start)
                overlap_end = min(highlight.end, kept_h.end)
                overlap = max(0, overlap_end - overlap_start)
                
                highlight_duration = highlight.end - highlight.start
                if overlap > highlight_duration * 0.5:  # >50% overlap
                    dominated = True
                    break
            
            if not dominated:
                kept.append(highlight)
        
        return kept
    
    def _fallback_chunk_highlights(self, chunk: dict, max_highlights: int) -> list[Highlight]:
        """Create basic highlights for a chunk when LLM fails"""
        highlights = []
        segments = chunk["segments"]
        
        if not segments:
            return []
        
        chunk_duration = chunk["end"] - chunk["start"]
        clip_duration = min(30.0, chunk_duration / max(max_highlights, 1))
        
        for i in range(min(max_highlights, 3)):
            start = chunk["start"] + i * (chunk_duration / max_highlights)
            end = min(start + clip_duration, chunk["end"])
            
            # Get text for this range
            clip_text = " ".join([
                seg.text for seg in segments
                if seg.start >= start and seg.end <= end
            ])
            
            highlights.append(Highlight(
                id=str(uuid.uuid4()),
                start=start,
                end=end,
                title=f"Highlight at {self._format_time(start)}",
                description=clip_text[:100] + "..." if len(clip_text) > 100 else clip_text,
                score=0.5 - (i * 0.05),
                tags=["auto-generated"],
                transcript_segment_ids=[]
            ))
        
        return highlights
    
    def _get_system_prompt(self) -> str:
        return """You are an expert content editor specializing in identifying viral-worthy moments 
in podcasts, interviews, and conversations. Your task is to analyze transcripts and identify 
the most engaging, shareable segments that would make great social media clips.

Focus on identifying moments with:
1. Strong emotional moments (excitement, surprise, humor, insight)
2. Clear, quotable statements that stand alone
3. Interesting stories or anecdotes with a clear beginning and payoff
4. Controversial or thought-provoking opinions
5. Educational "aha" moments that explain something clearly
6. Funny exchanges between speakers
7. Key insights or revelations
8. Memorable one-liners or soundbites

IMPORTANT: Look for highlights throughout the ENTIRE transcript section, not just the beginning.
Distribute your selections across the full timeline provided.

Always respond with valid JSON only, no other text."""
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    def _create_analysis_prompt(
        self,
        transcript: str,
        max_highlights: int,
        min_duration: float,
        max_duration: float,
        chunk_info: str = ""
    ) -> str:
        chunk_note = f"\n\nNOTE: {chunk_info}" if chunk_info else ""
        
        return f"""Analyze this transcript and identify up to {max_highlights} highlight clips.
{chunk_note}
IMPORTANT: 
- Find highlights distributed across the ENTIRE transcript, not just the beginning.
- Each clip should be between {min_duration:.0f} and {max_duration:.0f} seconds long.
- Use the EXACT timestamps from the transcript (e.g., if you see [45:30 - 46:00], use "45:30" and "46:00")

Transcript:
{transcript}

Return your analysis as a JSON array with this exact structure:
[
  {{
    "start_time": "HH:MM:SS or MM:SS (exact time from transcript)",
    "end_time": "HH:MM:SS or MM:SS (exact time from transcript)", 
    "title": "Short catchy title for the clip",
    "description": "Brief description of why this is a highlight",
    "score": 0.95,
    "tags": ["funny", "insight", "quotable"]
  }}
]

CRITICAL: The start_time and end_time MUST match timestamps shown in the transcript brackets [XX:XX].
Only return the JSON array, no other text.
Look for the BEST moments throughout, prioritizing quality and shareability."""
    
    def _parse_highlights(
        self,
        response: str,
        segments: list,
        min_duration: float,
        max_duration: float
    ) -> list[Highlight]:
        """Parse LLM response into Highlight objects"""
        highlights = []
        
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Handle markdown code blocks
            if response.startswith('```'):
                lines = response.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith('```') and not in_json:
                        in_json = True
                        continue
                    elif line.startswith('```') and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response = '\n'.join(json_lines)
            
            data = json.loads(response)
            
            for item in data:
                start = self._parse_time(item.get('start_time', '0:00'))
                end = self._parse_time(item.get('end_time', '0:30'))
                
                # Get the time range of segments for validation
                if segments:
                    seg_min = min(seg.start if hasattr(seg, 'start') else seg.get('start', 0) for seg in segments)
                    seg_max = max(seg.end if hasattr(seg, 'end') else seg.get('end', 0) for seg in segments)
                    
                    # If LLM returned 0-based times but we have actual timestamps, adjust
                    if start < seg_min and (seg_min - start) > 60:
                        # Likely LLM returned relative times - skip this or try to find nearest match
                        logger.warning(f"LLM returned 0-based time {start}, expected >= {seg_min}")
                        # Try to match the title/description to find the right segment
                        continue
                
                # Validate duration
                duration = end - start
                if duration < min_duration or duration > max_duration:
                    # Adjust to fit within bounds
                    if duration < min_duration:
                        end = start + min_duration
                    elif duration > max_duration:
                        end = start + max_duration
                
                # Find which transcript segments this covers
                segment_ids = []
                for seg in segments:
                    seg_id = seg.id if hasattr(seg, 'id') else seg.get('id', 0)
                    seg_start = seg.start if hasattr(seg, 'start') else seg.get('start', 0)
                    seg_end = seg.end if hasattr(seg, 'end') else seg.get('end', 0)
                    
                    if seg_start >= start and seg_end <= end:
                        segment_ids.append(seg_id)
                    elif seg_start <= start < seg_end:
                        segment_ids.append(seg_id)
                    elif seg_start < end <= seg_end:
                        segment_ids.append(seg_id)
                
                highlights.append(Highlight(
                    id=str(uuid.uuid4()),
                    start=start,
                    end=end,
                    title=item.get('title', 'Untitled Highlight'),
                    description=item.get('description', ''),
                    score=min(1.0, max(0.0, item.get('score', 0.5))),
                    tags=item.get('tags', []),
                    transcript_segment_ids=segment_ids
                ))
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing highlights: {e}")
        
        # Sort by score
        highlights.sort(key=lambda h: h.score, reverse=True)
        
        return highlights
    
    def _parse_time(self, time_str: str) -> float:
        """Parse MM:SS or HH:MM:SS to seconds"""
        parts = time_str.split(':')
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except ValueError:
            pass
        return 0.0
    
    async def _fallback_highlights(
        self,
        media_id: str,
        transcription: TranscriptionResult,
        max_highlights: int
    ) -> HighlightAnalysis:
        """Create basic highlights when LLM is unavailable"""
        logger.info("Using fallback highlight detection")
        
        highlights = []
        total_duration = transcription.segments[-1].end if transcription.segments else 0
        
        # Create evenly spaced highlights
        clip_duration = 30.0  # Default 30 second clips
        num_clips = min(max_highlights, int(total_duration / clip_duration))
        
        if num_clips == 0 and total_duration > 0:
            num_clips = 1
        
        interval = total_duration / max(num_clips, 1)
        
        for i in range(num_clips):
            start = i * interval
            end = min(start + clip_duration, total_duration)
            
            # Get transcript for this segment
            segment_ids = []
            clip_text = ""
            for seg in transcription.segments:
                if start <= seg.start < end:
                    segment_ids.append(seg.id)
                    clip_text += seg.text + " "
            
            highlights.append(Highlight(
                id=str(uuid.uuid4()),
                start=start,
                end=end,
                title=f"Clip {i + 1}",
                description=clip_text[:100] + "..." if len(clip_text) > 100 else clip_text,
                score=1.0 - (i * 0.1),  # Decreasing score
                tags=["auto-generated"],
                transcript_segment_ids=segment_ids
            ))
        
        return HighlightAnalysis(
            media_id=media_id,
            highlights=highlights
        )
    
    async def generate_caption(
        self, 
        transcript_text: str,
        platform: str = "twitter"
    ) -> str:
        """Generate a social media caption for a clip"""
        def _generate():
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'system',
                            'content': f'You are a social media expert. Generate engaging {platform} captions.'
                        },
                        {
                            'role': 'user',
                            'content': f'Create a short, engaging caption for this clip:\n\n{transcript_text}\n\nKeep it under 280 characters.'
                        }
                    ],
                    options={'temperature': 0.7}
                )
                return response['message']['content']
            except Exception as e:
                logger.error(f"Caption generation error: {e}")
                return transcript_text[:280]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate)


# Singleton instance
highlight_detector = HighlightDetector()

