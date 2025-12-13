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
        Analyze transcription and detect highlights across the FULL content.
        
        Task 2.5.5: Improved highlight discovery quality
        - Minimum highlight density heuristic (5-10 per hour)
        - Diversity constraints to avoid clustering
        - Combined signals: content, sentiment, speaker turns, emphasis
        - Re-ranking and scoring
        
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
        
        content_duration = end_time - start_time
        
        # Task 2.5.5: Minimum highlight density heuristic
        # Aim for 5-10 highlights per hour of content, but at least 3
        hours = content_duration / 3600
        min_expected_highlights = max(3, int(hours * 5))
        target_highlights = max(max_highlights, min_expected_highlights)
        
        logger.info(
            f"Content: {content_duration/60:.1f}min, "
            f"target: {target_highlights} highlights (min density: {min_expected_highlights})"
        )
        
        # Split into chunks for analysis
        chunks = self._create_chunks(transcription, start_time, end_time)
        logger.info(f"Analyzing {len(chunks)} chunks covering {end_time - start_time:.0f}s")
        
        # Calculate highlights per chunk to ensure even distribution
        # Request more than needed to have options for diversity filtering
        highlights_per_chunk = max(3, (target_highlights * 2) // len(chunks) + 1)
        
        # Detect signal-rich regions first
        signal_regions = self._detect_signal_regions(transcription.segments, start_time, end_time)
        
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
        
        # Task 2.5.5: Boost scores based on signal detection
        all_highlights = self._apply_signal_boost(all_highlights, signal_regions)
        
        # Deduplicate overlapping highlights
        all_highlights = self._deduplicate_highlights(all_highlights)
        
        # Task 2.5.5: Apply diversity constraints
        all_highlights = self._apply_diversity_constraints(
            all_highlights, 
            content_duration,
            target_highlights
        )
        
        # Sort by score and limit
        all_highlights.sort(key=lambda h: h.score, reverse=True)
        final_highlights = all_highlights[:max_highlights]
        
        # If we didn't get enough, generate fallbacks from signal regions
        if len(final_highlights) < min_expected_highlights:
            logger.info(
                f"Only {len(final_highlights)} highlights found, "
                f"generating {min_expected_highlights - len(final_highlights)} fallbacks"
            )
            fallbacks = self._generate_signal_fallbacks(
                transcription,
                signal_regions,
                final_highlights,
                min_expected_highlights - len(final_highlights),
                min_clip_duration,
                max_clip_duration
            )
            final_highlights.extend(fallbacks)
        
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
    
    def _detect_signal_regions(
        self,
        segments: list,
        start_time: float,
        end_time: float
    ) -> list[dict]:
        """
        Detect regions with strong highlight signals.
        
        Task 2.5.5: Combined signal detection
        - Speaker turns (conversation dynamics)
        - Emphasis markers (questions, exclamations)
        - Sentiment shifts
        - Key phrases
        """
        regions = []
        
        # Filter segments to time range
        range_segments = [
            s for s in segments 
            if s.start >= start_time and s.end <= end_time
        ]
        
        if not range_segments:
            return []
        
        # Emphasis patterns
        emphasis_patterns = [
            (r'\?', 'question', 0.2),
            (r'!', 'exclamation', 0.3),
            (r'\bwow\b|\bamazing\b|\bincredible\b', 'amazement', 0.4),
            (r'\bactually\b|\binteresting\b', 'insight', 0.2),
            (r'\bfunny\b|\bhilarious\b|\blaughing\b|\blol\b', 'humor', 0.4),
            (r'\bi think\b|\bin my opinion\b|\bi believe\b', 'opinion', 0.3),
            (r'\bthe key\b|\bimportant\b|\bcrucial\b', 'key_point', 0.3),
            (r'\bsecret\b|\btrick\b|\bhack\b|\btip\b', 'tip', 0.35),
        ]
        
        import re
        
        # Analyze segments in windows
        window_size = 5  # segments per window
        for i in range(0, len(range_segments), window_size // 2):
            window = range_segments[i:i + window_size]
            if not window:
                continue
            
            window_start = window[0].start
            window_end = window[-1].end
            window_text = " ".join(s.text for s in window)
            
            # Calculate signal score
            signal_score = 0.0
            tags = []
            
            # Check emphasis patterns
            for pattern, tag, boost in emphasis_patterns:
                matches = re.findall(pattern, window_text.lower())
                if matches:
                    signal_score += boost * min(len(matches), 3)
                    tags.append(tag)
            
            # Check for speaker turns (conversation dynamics)
            speakers = set(s.speaker for s in window if s.speaker)
            if len(speakers) > 1:
                signal_score += 0.3
                tags.append('dialogue')
            
            # Check for longer sentences (often more substantive)
            avg_length = sum(len(s.text.split()) for s in window) / len(window)
            if avg_length > 15:
                signal_score += 0.15
                tags.append('substantive')
            
            if signal_score > 0.3:
                regions.append({
                    'start': window_start,
                    'end': window_end,
                    'score': min(1.0, signal_score),
                    'tags': tags
                })
        
        return regions
    
    def _apply_signal_boost(
        self,
        highlights: list[Highlight],
        signal_regions: list[dict]
    ) -> list[Highlight]:
        """Boost highlight scores based on signal detection"""
        for highlight in highlights:
            # Find overlapping signal regions
            for region in signal_regions:
                overlap_start = max(highlight.start, region['start'])
                overlap_end = min(highlight.end, region['end'])
                overlap = max(0, overlap_end - overlap_start)
                
                highlight_duration = highlight.end - highlight.start
                if overlap > highlight_duration * 0.3:  # >30% overlap
                    # Boost score based on signal strength
                    boost = region['score'] * 0.2
                    highlight.score = min(1.0, highlight.score + boost)
                    
                    # Add signal tags if not already present
                    for tag in region['tags']:
                        if tag not in highlight.tags:
                            highlight.tags.append(tag)
        
        return highlights
    
    def _apply_diversity_constraints(
        self,
        highlights: list[Highlight],
        content_duration: float,
        target_count: int
    ) -> list[Highlight]:
        """
        Apply diversity constraints to avoid clustering.
        
        Ensures highlights are spread across the content timeline.
        """
        if not highlights or target_count <= 0:
            return highlights
        
        # Sort by score first
        highlights.sort(key=lambda h: h.score, reverse=True)
        
        # Minimum spacing between highlights (aim for even distribution)
        min_spacing = content_duration / (target_count + 1) * 0.5  # 50% of even spacing
        
        selected = []
        for highlight in highlights:
            # Check spacing from already selected highlights
            too_close = False
            for selected_h in selected:
                distance = abs(highlight.start - selected_h.start)
                if distance < min_spacing:
                    too_close = True
                    break
            
            if not too_close:
                selected.append(highlight)
        
        # If diversity filtering removed too many, relax constraints
        if len(selected) < target_count * 0.5:
            # Add back some clustered highlights
            for highlight in highlights:
                if highlight not in selected and len(selected) < target_count:
                    selected.append(highlight)
        
        return selected
    
    def _generate_signal_fallbacks(
        self,
        transcription: TranscriptionResult,
        signal_regions: list[dict],
        existing_highlights: list[Highlight],
        count: int,
        min_duration: float,
        max_duration: float
    ) -> list[Highlight]:
        """Generate fallback highlights from signal-rich regions"""
        fallbacks = []
        
        # Sort signal regions by score
        signal_regions.sort(key=lambda r: r['score'], reverse=True)
        
        existing_ranges = [(h.start, h.end) for h in existing_highlights]
        
        for region in signal_regions:
            if len(fallbacks) >= count:
                break
            
            # Check if this region overlaps with existing highlights
            overlaps = False
            for start, end in existing_ranges:
                if max(region['start'], start) < min(region['end'], end):
                    overlaps = True
                    break
            
            if overlaps:
                continue
            
            # Create a highlight from this region
            duration = region['end'] - region['start']
            if duration < min_duration:
                # Extend the region
                end = min(region['start'] + min_duration, transcription.segments[-1].end)
            elif duration > max_duration:
                end = region['start'] + max_duration
            else:
                end = region['end']
            
            # Get text for title/description
            region_segments = [
                s for s in transcription.segments
                if s.start >= region['start'] and s.end <= end
            ]
            
            if not region_segments:
                continue
            
            text = " ".join(s.text for s in region_segments)
            title = text[:50] + "..." if len(text) > 50 else text
            
            fallbacks.append(Highlight(
                id=str(uuid.uuid4()),
                start=region['start'],
                end=end,
                title=f"Highlight: {title}",
                description=text[:200] + "..." if len(text) > 200 else text,
                score=region['score'] * 0.8,  # Slightly lower score for fallbacks
                tags=region.get('tags', ['auto-detected']),
                transcript_segment_ids=[s.id for s in region_segments]
            ))
            
            existing_ranges.append((region['start'], end))
        
        return fallbacks
    
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
        """
        Parse LLM response into Highlight objects with timestamp validation.
        
        Task 2.5.4: Highlight timing alignment bug
        - Validates timestamps against segment boundaries
        - Clamps timestamps to valid ranges
        - Rejects highlights with impossible timestamps
        """
        highlights = []
        
        # Pre-compute segment boundaries for validation
        if not segments:
            return []
        
        seg_min = min(seg.start if hasattr(seg, 'start') else seg.get('start', 0) for seg in segments)
        seg_max = max(seg.end if hasattr(seg, 'end') else seg.get('end', 0) for seg in segments)
        
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
                # Parse timestamps with NO default fallbacks
                start_str = item.get('start_time')
                end_str = item.get('end_time')
                
                # Reject if LLM didn't provide timestamps
                if not start_str or not end_str:
                    logger.warning(f"Highlight missing timestamps, skipping: {item.get('title', 'Untitled')}")
                    continue
                
                start = self._parse_time(start_str)
                end = self._parse_time(end_str)
                
                # Task 2.5.4: Validate and correct timestamps
                # 
                # If LLM returned 0-based times but chunk starts later, 
                # try to offset by chunk start time
                if start < seg_min and (seg_min - start) > 60:
                    offset = seg_min
                    adjusted_start = start + offset
                    adjusted_end = end + offset
                    
                    # Check if adjusted times are within bounds
                    if adjusted_start >= seg_min and adjusted_end <= seg_max + 30:  # Allow 30s slack
                        logger.info(f"Adjusted 0-based timestamp: {start} -> {adjusted_start}")
                        start = adjusted_start
                        end = adjusted_end
                    else:
                        logger.warning(
                            f"Cannot correct timestamp for highlight '{item.get('title', '')}': "
                            f"start={start}, seg_min={seg_min}, seg_max={seg_max}"
                        )
                        continue
                
                # Clamp to valid segment range
                start = max(seg_min, start)
                end = min(seg_max, end)
                
                # Reject if timestamps are now invalid
                if start >= end:
                    logger.warning(f"Invalid timestamp range after clamping: {start} >= {end}")
                    continue
                
                # Validate duration
                duration = end - start
                if duration < min_duration or duration > max_duration:
                    # Adjust to fit within bounds
                    if duration < min_duration:
                        # Extend end if possible
                        new_end = start + min_duration
                        if new_end <= seg_max:
                            end = new_end
                        else:
                            # Try extending start backwards
                            new_start = end - min_duration
                            if new_start >= seg_min:
                                start = new_start
                            else:
                                logger.warning(f"Cannot create minimum duration clip at {start}")
                                continue
                    elif duration > max_duration:
                        end = start + max_duration
                
                # Final sanity check
                if start < 0 or end < 0 or start >= end:
                    logger.warning(f"Final sanity check failed: start={start}, end={end}")
                    continue
                
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
    
    def validate_and_fix_highlights(
        self,
        highlights: list[Highlight],
        media_duration: float
    ) -> list[Highlight]:
        """
        Validate and fix highlight timestamps.
        
        Task 2.5.4: Data integrity check for existing highlights.
        
        Args:
            highlights: List of highlights to validate
            media_duration: Total media duration in seconds
            
        Returns:
            List of valid highlights with corrected timestamps
        """
        valid_highlights = []
        
        for highlight in highlights:
            start = highlight.start
            end = highlight.end
            
            # Check for obviously invalid timestamps
            if start < 0:
                logger.warning(f"Highlight {highlight.id} has negative start time, clamping to 0")
                start = 0
            
            if end > media_duration:
                logger.warning(
                    f"Highlight {highlight.id} end time ({end}s) exceeds duration ({media_duration}s), clamping"
                )
                end = media_duration
            
            if start >= end:
                logger.warning(
                    f"Highlight {highlight.id} has invalid range: {start} >= {end}, skipping"
                )
                continue
            
            # Check for suspiciously short highlights
            duration = end - start
            if duration < 5:
                logger.warning(
                    f"Highlight {highlight.id} is suspiciously short ({duration}s), extending to 15s"
                )
                end = min(start + 15, media_duration)
            
            # Check for highlights at exactly 0:00 (often a bug)
            if start == 0 and end <= 30 and media_duration > 120:
                # Highlight at very start of long media is suspicious
                logger.warning(
                    f"Highlight {highlight.id} is at media start (0:00), may be invalid"
                )
                # Don't skip, but lower the score
                highlight.score = highlight.score * 0.5
            
            # Create corrected highlight
            valid_highlights.append(Highlight(
                id=highlight.id,
                start=start,
                end=end,
                title=highlight.title,
                description=highlight.description,
                score=highlight.score,
                tags=highlight.tags,
                transcript_segment_ids=highlight.transcript_segment_ids
            ))
        
        return valid_highlights


# Singleton instance
highlight_detector = HighlightDetector()

