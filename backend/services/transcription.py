"""
Transcription service using OpenAI Whisper (local) with speaker diarization
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional
import whisper

from config import settings
from models import TranscriptSegment, TranscriptionResult

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Handles audio/video transcription using Whisper with speaker diarization"""
    
    def __init__(self):
        self._model = None
        self._model_name = settings.whisper_model
        self._diarization = None
    
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
    
    async def transcribe(
        self, 
        media_id: str,
        file_path: Path,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio/video file
        
        Args:
            media_id: Unique identifier for the media
            file_path: Path to the media file
            language: Optional language code (auto-detect if None)
        
        Returns:
            TranscriptionResult with segments and full text
        """
        logger.info(f"Starting transcription for {media_id}")
        
        def _transcribe():
            options = {
                'task': 'transcribe',
                'verbose': False,
                'word_timestamps': True,  # Get word-level timing for better diarization
            }
            
            if language:
                options['language'] = language
            
            result = self.model.transcribe(str(file_path), **options)
            return result
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _transcribe)
        
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
        
        logger.info(f"Transcription complete for {media_id}: {len(segments)} segments")
        
        return TranscriptionResult(
            media_id=media_id,
            language=detected_language,
            segments=segments,
            full_text=full_text,
        )
    
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

