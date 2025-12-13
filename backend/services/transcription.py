"""
Transcription service using OpenAI Whisper (local) with speaker diarization

Supports:
- Chunked processing for long-form content (>10 min)
- Retry logic with exponential backoff
- Progress callbacks for real-time UI updates
"""
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable, List
import whisper

from config import settings
from models import TranscriptSegment, TranscriptionResult

logger = logging.getLogger(__name__)

# Configuration for chunked processing
CHUNK_DURATION_SECONDS = 600  # 10 minutes per chunk
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # Exponential backoff base (seconds)
LONG_FORM_THRESHOLD = 600  # Files > 10 min trigger chunked processing


class TranscriptionService:
    """
    Handles audio/video transcription using Whisper with speaker diarization.
    
    Features:
    - Chunked processing for long-form content (podcasts, lectures, etc.)
    - Retry logic with exponential backoff for resilience
    - Progress callbacks for real-time UI updates
    """
    
    def __init__(self):
        self._model = None
        self._model_name = settings.whisper_model
        self._diarization = None
        # Progress callback for real-time updates
        self._progress_callback: Optional[Callable[[float, str], None]] = None
    
    @property
    def model(self):
        """Lazy load the Whisper model"""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self._model_name}")
            self._model = whisper.load_model(self._model_name)
            logger.info("Whisper model loaded successfully")
        return self._model
    
    @property
    def diarization(self):
        """Lazy load speaker diarization service"""
        if self._diarization is None:
            from services.speaker_diarization import speaker_diarization
            self._diarization = speaker_diarization
        return self._diarization
    
    def set_progress_callback(self, callback: Optional[Callable[[float, str], None]]):
        """
        Set a callback for progress updates.
        
        Args:
            callback: Function(progress: float, message: str) where progress is 0.0-1.0
        """
        self._progress_callback = callback
    
    def _report_progress(self, progress: float, message: str):
        """Report progress if callback is set"""
        if self._progress_callback:
            try:
                self._progress_callback(progress, message)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    async def _get_audio_duration(self, file_path: Path) -> float:
        """Get audio/video duration using ffprobe"""
        def _probe():
            try:
                cmd = [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(file_path)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return float(result.stdout.strip())
            except Exception as e:
                logger.warning(f"Could not get duration: {e}")
                return 0.0
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _probe)
    
    async def _extract_audio_chunk(
        self, 
        file_path: Path, 
        start: float, 
        duration: float,
        output_path: Path
    ) -> bool:
        """Extract a chunk of audio using ffmpeg"""
        def _extract():
            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(start),
                    '-i', str(file_path),
                    '-t', str(duration),
                    '-vn',  # No video
                    '-acodec', 'pcm_s16le',  # WAV format for Whisper
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',  # Mono
                    str(output_path)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Chunk extraction error: {e}")
                return False
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract)
    
    async def _transcribe_with_retry(
        self,
        file_path: Path,
        language: Optional[str] = None,
        max_retries: int = MAX_RETRIES
    ) -> dict:
        """
        Transcribe with retry logic and exponential backoff.
        
        Args:
            file_path: Path to audio file
            language: Optional language code
            max_retries: Maximum retry attempts
            
        Returns:
            Whisper transcription result dict
            
        Raises:
            RuntimeError: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                def _transcribe():
                    options = {
                        'task': 'transcribe',
                        'verbose': False,
                        'word_timestamps': True,
                    }
                    if language:
                        options['language'] = language
                    return self.model.transcribe(str(file_path), **options)
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, _transcribe)
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(
                        f"Transcription attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_retries} transcription attempts failed")
        
        raise RuntimeError(f"Transcription failed after {max_retries} attempts: {last_error}")
    
    async def transcribe(
        self, 
        media_id: str,
        file_path: Path,
        language: Optional[str] = None,
        force_chunked: bool = False
    ) -> TranscriptionResult:
        """
        Transcribe audio/video file with automatic chunking for long content.
        
        Args:
            media_id: Unique identifier for the media
            file_path: Path to the media file
            language: Optional language code (auto-detect if None)
            force_chunked: Force chunked processing even for short files
        
        Returns:
            TranscriptionResult with segments and full text
        """
        logger.info(f"Starting transcription for {media_id}")
        self._report_progress(0.0, "Analyzing audio file...")
        
        # Get duration to decide processing strategy
        duration = await self._get_audio_duration(file_path)
        logger.info(f"Media duration: {duration:.1f}s")
        
        # Use chunked processing for long-form content
        if duration > LONG_FORM_THRESHOLD or force_chunked:
            logger.info(f"Using chunked processing for long-form content ({duration:.1f}s)")
            return await self._transcribe_chunked(media_id, file_path, duration, language)
        
        # Standard transcription for shorter content
        self._report_progress(0.1, "Transcribing audio...")
        
        result = await self._transcribe_with_retry(file_path, language)
        
        self._report_progress(0.9, "Processing segments...")
        
        # Convert to our segment format
        segments = []
        for i, seg in enumerate(result['segments']):
            segments.append(TranscriptSegment(
                id=i,
                start=seg['start'],
                end=seg['end'],
                text=seg['text'].strip(),
                confidence=seg.get('avg_logprob', 0) if seg.get('avg_logprob') else 1.0,
            ))
        
        full_text = result['text'].strip()
        detected_language = result.get('language', 'en')
        
        self._report_progress(1.0, "Transcription complete")
        logger.info(f"Transcription complete for {media_id}: {len(segments)} segments")
        
        return TranscriptionResult(
            media_id=media_id,
            language=detected_language,
            segments=segments,
            full_text=full_text,
        )
    
    async def _transcribe_chunked(
        self,
        media_id: str,
        file_path: Path,
        duration: float,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe long-form content in chunks.
        
        This approach:
        1. Splits audio into 10-minute chunks
        2. Transcribes each chunk with retry logic
        3. Merges segments with corrected timestamps
        4. Reports progress for each chunk
        
        Args:
            media_id: Unique identifier for the media
            file_path: Path to the media file
            duration: Total duration in seconds
            language: Optional language code
            
        Returns:
            TranscriptionResult with merged segments
        """
        # Calculate chunks
        num_chunks = int(duration / CHUNK_DURATION_SECONDS) + 1
        all_segments: List[TranscriptSegment] = []
        full_text_parts: List[str] = []
        detected_language = 'en'
        
        logger.info(f"Processing {num_chunks} chunks for {duration:.1f}s audio")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for chunk_idx in range(num_chunks):
                chunk_start = chunk_idx * CHUNK_DURATION_SECONDS
                chunk_duration = min(CHUNK_DURATION_SECONDS, duration - chunk_start)
                
                if chunk_duration <= 0:
                    break
                
                # Progress calculation
                chunk_progress = chunk_idx / num_chunks
                self._report_progress(
                    chunk_progress * 0.9,  # Reserve 10% for final processing
                    f"Transcribing chunk {chunk_idx + 1}/{num_chunks} "
                    f"({int(chunk_start / 60)}:{int(chunk_start % 60):02d} - "
                    f"{int((chunk_start + chunk_duration) / 60)}:{int((chunk_start + chunk_duration) % 60):02d})"
                )
                
                # Extract chunk
                chunk_file = temp_path / f"chunk_{chunk_idx}.wav"
                success = await self._extract_audio_chunk(
                    file_path, chunk_start, chunk_duration, chunk_file
                )
                
                if not success:
                    logger.error(f"Failed to extract chunk {chunk_idx}")
                    continue
                
                try:
                    # Transcribe chunk with retry logic
                    result = await self._transcribe_with_retry(chunk_file, language)
                    
                    # Update detected language from first chunk
                    if chunk_idx == 0:
                        detected_language = result.get('language', 'en')
                    
                    # Merge segments with time offset
                    segment_offset = len(all_segments)
                    for i, seg in enumerate(result['segments']):
                        all_segments.append(TranscriptSegment(
                            id=segment_offset + i,
                            start=seg['start'] + chunk_start,  # Add time offset
                            end=seg['end'] + chunk_start,
                            text=seg['text'].strip(),
                            confidence=seg.get('avg_logprob', 0) if seg.get('avg_logprob') else 1.0,
                        ))
                    
                    full_text_parts.append(result['text'].strip())
                    
                    logger.info(
                        f"Chunk {chunk_idx + 1}/{num_chunks} complete: "
                        f"{len(result['segments'])} segments"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to transcribe chunk {chunk_idx}: {e}")
                    # Continue with remaining chunks
                finally:
                    # Clean up chunk file
                    if chunk_file.exists():
                        chunk_file.unlink()
        
        self._report_progress(0.95, "Merging transcription segments...")
        
        # Merge overlapping segments if any
        merged_segments = self._merge_overlapping_segments(all_segments)
        
        # Combine full text
        full_text = " ".join(full_text_parts)
        
        self._report_progress(1.0, "Transcription complete")
        logger.info(
            f"Chunked transcription complete for {media_id}: "
            f"{len(merged_segments)} segments from {num_chunks} chunks"
        )
        
        return TranscriptionResult(
            media_id=media_id,
            language=detected_language,
            segments=merged_segments,
            full_text=full_text,
        )
    
    def _merge_overlapping_segments(
        self, 
        segments: List[TranscriptSegment]
    ) -> List[TranscriptSegment]:
        """
        Merge segments that may overlap at chunk boundaries.
        
        Args:
            segments: List of segments potentially with overlaps
            
        Returns:
            Merged and renumbered segments
        """
        if not segments:
            return []
        
        # Sort by start time
        sorted_segs = sorted(segments, key=lambda s: s.start)
        merged = [sorted_segs[0]]
        
        for seg in sorted_segs[1:]:
            last = merged[-1]
            
            # Check for overlap (within 0.5s tolerance at chunk boundaries)
            if seg.start <= last.end + 0.5:
                # Segments overlap - merge if text is similar
                # Otherwise keep both (different speakers might overlap)
                if seg.text.strip() == last.text.strip():
                    # Duplicate - extend end time and skip
                    last.end = max(last.end, seg.end)
                else:
                    # Different content - keep both
                    merged.append(seg)
            else:
                merged.append(seg)
        
        # Renumber IDs
        for i, seg in enumerate(merged):
            seg.id = i
        
        return merged
    
    async def transcribe_with_speakers(
        self,
        media_id: str,
        file_path: Path,
        language: Optional[str] = None,
        num_speakers: Optional[int] = None
    ) -> TranscriptionResult:
        """
        Transcribe with speaker diarization
        
        Uses pyannote.audio for accurate speaker detection when available,
        falls back to energy-based detection otherwise.
        
        Args:
            media_id: Unique identifier for the media
            file_path: Path to the media file
            language: Optional language code
            num_speakers: Exact number of speakers if known
        
        Returns:
            TranscriptionResult with speaker labels
        """
        # Run transcription first (more reliable)
        logger.info(f"Starting transcription with speaker diarization for {media_id}")
        
        transcription_result = await self.transcribe(media_id, file_path, language)
        
        # Try diarization separately - it may fail on some files
        diarization_segments = []
        try:
            diarization_segments = await self.diarization.diarize(
                file_path,
                num_speakers=num_speakers,
                min_speakers=1,
                max_speakers=10
            )
        except Exception as e:
            logger.warning(f"Diarization failed: {e}")
            diarization_segments = []
        
        # Merge diarization with transcription if we got results
        if diarization_segments and len(diarization_segments) > 0:
            # Convert segments to dicts for merging
            segment_dicts = [
                {
                    "id": seg.id,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "confidence": seg.confidence,
                    "speaker": seg.speaker
                }
                for seg in transcription_result.segments
            ]
            
            # Merge speaker labels
            merged = self.diarization.merge_with_transcript(
                segment_dicts,
                diarization_segments
            )
            
            # Convert back to TranscriptSegment objects
            transcription_result.segments = [
                TranscriptSegment(
                    id=seg["id"],
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                    speaker=seg.get("speaker"),
                    confidence=seg["confidence"]
                )
                for seg in merged
            ]
            
            # Count unique speakers
            speakers = set(seg.speaker for seg in transcription_result.segments if seg.speaker)
            logger.info(f"Diarization identified {len(speakers)} speakers")
        else:
            # Fallback to simple heuristic if diarization failed
            logger.warning("Diarization failed, using fallback speaker detection")
            await self._apply_fallback_speakers(transcription_result)
        
        return transcription_result
    
    async def _apply_fallback_speakers(self, result: TranscriptionResult):
        """Apply simple heuristic-based speaker detection as fallback"""
        if not result.segments:
            return
        
        current_speaker = 1
        prev_end = 0
        
        for segment in result.segments:
            gap = segment.start - prev_end
            
            # Speaker likely changed if:
            # - Long pause (> 1.5s)
            # - Very short segment followed by longer one (interruption pattern)
            if gap > 1.5:
                current_speaker = 2 if current_speaker == 1 else 1
            elif gap > 0.8 and len(segment.text) > 50:
                # Might be a new speaker taking over
                current_speaker = 2 if current_speaker == 1 else 1
            
            segment.speaker = f"Speaker {current_speaker}"
            prev_end = segment.end


# Singleton instance
transcription_service = TranscriptionService()

