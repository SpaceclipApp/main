"""
Speaker diarization service using pyannote.audio for accurate speaker detection
Falls back to energy-based detection if pyannote is unavailable
"""
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import pyannote - it's optional but recommended
PYANNOTE_AVAILABLE = False
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    logger.warning("pyannote.audio not available. Using fallback speaker detection.")


class SpeakerDiarization:
    """
    Handles speaker diarization (who spoke when)
    
    Uses pyannote.audio for accurate diarization when available,
    falls back to energy-based heuristics otherwise.
    """
    
    def __init__(self):
        self._pipeline = None
        self._model_loaded = False
    
    @property
    def pipeline(self):
        """Lazy load pyannote pipeline"""
        if not PYANNOTE_AVAILABLE:
            return None
        
        if self._pipeline is None and not self._model_loaded:
            try:
                # Use the pre-trained speaker diarization pipeline
                # Note: Requires accepting pyannote terms on HuggingFace
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=None  # Set HF_TOKEN env var if needed
                )
                self._model_loaded = True
                logger.info("Loaded pyannote speaker diarization model")
            except Exception as e:
                logger.warning(f"Could not load pyannote model: {e}")
                self._model_loaded = True  # Don't retry
        
        return self._pipeline
    
    async def diarize(
        self, 
        audio_path: Path,
        num_speakers: Optional[int] = None,
        min_speakers: int = 1,
        max_speakers: int = 10
    ) -> list[dict]:
        """
        Perform speaker diarization on audio file
        
        Args:
            audio_path: Path to audio file
            num_speakers: Exact number of speakers (if known)
            min_speakers: Minimum expected speakers
            max_speakers: Maximum expected speakers
        
        Returns:
            List of segments: [{"start": float, "end": float, "speaker": str}]
        """
        if self.pipeline is not None:
            return await self._diarize_pyannote(
                audio_path, num_speakers, min_speakers, max_speakers
            )
        else:
            return await self._diarize_fallback(audio_path)
    
    async def _diarize_pyannote(
        self,
        audio_path: Path,
        num_speakers: Optional[int],
        min_speakers: int,
        max_speakers: int
    ) -> list[dict]:
        """Use pyannote.audio for accurate diarization"""
        
        def _run_diarization():
            # Configure pipeline parameters
            params = {}
            if num_speakers is not None:
                params["num_speakers"] = num_speakers
            else:
                params["min_speakers"] = min_speakers
                params["max_speakers"] = max_speakers
            
            # Run diarization
            diarization = self.pipeline(str(audio_path), **params)
            
            # Convert to our format
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
            
            return segments
        
        loop = asyncio.get_event_loop()
        segments = await loop.run_in_executor(None, _run_diarization)
        
        # Rename speakers to friendly names
        speaker_map = {}
        for seg in segments:
            if seg["speaker"] not in speaker_map:
                speaker_map[seg["speaker"]] = f"Speaker {len(speaker_map) + 1}"
            seg["speaker"] = speaker_map[seg["speaker"]]
        
        logger.info(f"Diarization found {len(speaker_map)} speakers, {len(segments)} segments")
        return segments
    
    async def _diarize_fallback(self, audio_path: Path) -> list[dict]:
        """
        Fallback: Use energy-based voice activity detection + clustering
        This is less accurate but works without pyannote
        """
        logger.info("Using fallback speaker detection (energy-based)")
        
        try:
            # Extract audio features using ffmpeg
            segments = await self._detect_speech_segments(audio_path)
            
            if not segments or len(segments) == 0:
                logger.warning("No speech segments detected, returning empty list")
                return []
            
            # Simple clustering based on audio characteristics
            segments = self._cluster_speakers_simple(segments, audio_path)
            
            return segments
        except Exception as e:
            logger.error(f"Fallback diarization failed: {e}")
            return []
    
    async def _detect_speech_segments(self, audio_path: Path) -> list[dict]:
        """Detect speech segments using energy thresholding"""
        
        def _analyze():
            try:
                cmd = [
                    'ffmpeg', '-y', '-i', str(audio_path),
                    '-af', 'silencedetect=noise=-30dB:d=0.5',
                    '-f', 'null', '-'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                stderr = result.stderr
                
                # Parse silence detection output
                segments = []
                current_start = 0.0
                
                for line in stderr.split('\n'):
                    if 'silence_start' in line:
                        try:
                            parts = line.split('silence_start:')
                            if len(parts) > 1:
                                end_time = float(parts[1].strip().split()[0])
                                if end_time > current_start + 0.5:
                                    segments.append({
                                        "start": current_start,
                                        "end": end_time,
                                        "speaker": "Unknown"
                                    })
                        except (ValueError, IndexError):
                            pass
                            
                    elif 'silence_end' in line:
                        try:
                            parts = line.split('silence_end:')
                            if len(parts) > 1:
                                current_start = float(parts[1].strip().split()[0])
                        except (ValueError, IndexError):
                            pass
                
                return segments
            except Exception as e:
                logger.warning(f"Speech segment detection failed: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _analyze)
    
    def _cluster_speakers_simple(
        self, 
        segments: list[dict], 
        audio_path: Path
    ) -> list[dict]:
        """
        Simple speaker clustering based on segment patterns
        
        This uses basic heuristics:
        - Segments close together are likely same speaker
        - Long pauses suggest speaker change
        - Alternating patterns suggest conversation
        """
        if len(segments) <= 1:
            for seg in segments:
                seg["speaker"] = "Speaker 1"
            return segments
        
        # Analyze gaps between segments
        gaps = []
        for i in range(1, len(segments)):
            gap = segments[i]["start"] - segments[i-1]["end"]
            gaps.append(gap)
        
        if not gaps:
            for seg in segments:
                seg["speaker"] = "Speaker 1"
            return segments
        
        # Threshold for speaker change (adaptive based on content)
        median_gap = sorted(gaps)[len(gaps) // 2]
        speaker_change_threshold = max(1.5, median_gap * 2)
        
        # Assign speakers
        current_speaker = 1
        max_speakers = 2  # Start with assumption of 2 speakers
        speaker_history = []
        
        for i, seg in enumerate(segments):
            if i == 0:
                seg["speaker"] = f"Speaker {current_speaker}"
                speaker_history.append(current_speaker)
            else:
                gap = seg["start"] - segments[i-1]["end"]
                
                if gap > speaker_change_threshold:
                    # Likely speaker change
                    # Alternate between speakers for conversation pattern
                    if len(speaker_history) >= 2:
                        # Look at recent pattern
                        recent = speaker_history[-3:] if len(speaker_history) >= 3 else speaker_history
                        if recent[-1] == 1:
                            current_speaker = 2
                        else:
                            current_speaker = 1
                    else:
                        current_speaker = 2 if current_speaker == 1 else 1
                
                seg["speaker"] = f"Speaker {current_speaker}"
                speaker_history.append(current_speaker)
        
        return segments
    
    def merge_with_transcript(
        self,
        transcript_segments: list[dict],
        diarization_segments: list[dict]
    ) -> list[dict]:
        """
        Merge diarization results with transcript segments
        
        Assigns speaker labels to transcript segments based on
        which speaker was active during that time.
        """
        if not diarization_segments:
            return transcript_segments
        
        for trans_seg in transcript_segments:
            trans_start = trans_seg.get("start", 0)
            trans_end = trans_seg.get("end", trans_start + 1)
            trans_mid = (trans_start + trans_end) / 2
            
            # Find which speaker was active at the midpoint
            best_speaker = None
            best_overlap = 0
            
            for diar_seg in diarization_segments:
                diar_start = diar_seg["start"]
                diar_end = diar_seg["end"]
                
                # Calculate overlap
                overlap_start = max(trans_start, diar_start)
                overlap_end = min(trans_end, diar_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diar_seg["speaker"]
            
            if best_speaker:
                trans_seg["speaker"] = best_speaker
        
        return transcript_segments


# Singleton instance
speaker_diarization = SpeakerDiarization()

