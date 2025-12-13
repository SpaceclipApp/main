from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class SourceType(str, Enum):
    UPLOAD = "upload"
    YOUTUBE = "youtube"
    X_SPACE = "x_space"
    URL = "url"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


class Platform(str, Enum):
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    YOUTUBE_SHORTS = "youtube_shorts"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"


class PlatformSpec(BaseModel):
    """Platform-specific export specifications"""
    platform: Platform
    width: int
    height: int
    max_duration: int  # seconds
    aspect_ratio: str


PLATFORM_SPECS = {
    Platform.INSTAGRAM_FEED: PlatformSpec(
        platform=Platform.INSTAGRAM_FEED,
        width=1080, height=1080, max_duration=60, aspect_ratio="1:1"
    ),
    Platform.INSTAGRAM_REELS: PlatformSpec(
        platform=Platform.INSTAGRAM_REELS,
        width=1080, height=1920, max_duration=90, aspect_ratio="9:16"
    ),
    Platform.TIKTOK: PlatformSpec(
        platform=Platform.TIKTOK,
        width=1080, height=1920, max_duration=180, aspect_ratio="9:16"
    ),
    Platform.YOUTUBE: PlatformSpec(
        platform=Platform.YOUTUBE,
        width=1920, height=1080, max_duration=3600, aspect_ratio="16:9"
    ),
    Platform.YOUTUBE_SHORTS: PlatformSpec(
        platform=Platform.YOUTUBE_SHORTS,
        width=1080, height=1920, max_duration=60, aspect_ratio="9:16"
    ),
    Platform.LINKEDIN: PlatformSpec(
        platform=Platform.LINKEDIN,
        width=1920, height=1080, max_duration=600, aspect_ratio="16:9"
    ),
    Platform.TWITTER: PlatformSpec(
        platform=Platform.TWITTER,
        width=1280, height=720, max_duration=140, aspect_ratio="16:9"
    ),
}


class TranscriptSegment(BaseModel):
    """A segment of transcribed text"""
    id: int
    start: float  # seconds
    end: float  # seconds
    text: str
    speaker: Optional[str] = None
    confidence: float = 1.0


class Highlight(BaseModel):
    """An AI-detected highlight/clip suggestion"""
    id: str
    start: float
    end: float
    title: str
    description: str
    score: float = Field(ge=0, le=1)
    tags: list[str] = []
    transcript_segment_ids: list[int] = []


class MediaUploadRequest(BaseModel):
    """Request to process media from URL"""
    url: str
    source_type: SourceType


class MediaInfo(BaseModel):
    """Information about uploaded/processed media"""
    id: str
    filename: str
    original_filename: Optional[str] = None
    media_type: MediaType
    source_type: SourceType
    source_url: Optional[str] = None  # Original URL for YouTube/X Spaces
    duration: float  # seconds
    file_path: str
    thumbnail_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TranscriptionResult(BaseModel):
    """Full transcription result"""
    media_id: str
    language: str
    segments: list[TranscriptSegment]
    full_text: str


class HighlightAnalysis(BaseModel):
    """AI highlight analysis result"""
    media_id: str
    highlights: list[Highlight]
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class ClipRequest(BaseModel):
    """Request to create a clip"""
    media_id: str
    start: float
    end: float
    title: Optional[str] = None
    platforms: list[Platform]
    include_captions: bool = True
    audiogram_style: Optional[str] = "waveform"


class ClipResult(BaseModel):
    """Generated clip information"""
    id: str
    media_id: str
    platform: Platform
    file_path: str
    duration: float
    width: int
    height: int
    has_captions: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectStatusResponse(BaseModel):
    """Response for project status polling"""
    media_id: str
    status: ProcessingStatus
    progress: float = Field(ge=0, le=1)
    status_message: Optional[str] = None
    error: Optional[str] = None
    has_transcription: bool = False
    has_highlights: bool = False
    clip_count: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectState(BaseModel):
    """Full project state for frontend"""
    # Owner of this project (derived from the project's user)
    user_id: Optional[str] = None

    # ID of the logical project / folder row in the DB
    project_id: Optional[str] = None

    media: Optional[MediaInfo] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    status_message: Optional[str] = None  # Detailed status message for UI
    error: Optional[str] = None
    transcription: Optional[TranscriptionResult] = None
    highlights: Optional[HighlightAnalysis] = None
    clips: list[ClipResult] = []


