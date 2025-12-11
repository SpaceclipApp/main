"""
SQLAlchemy ORM models for Transcription and TranscriptSegment tables
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .media_model import MediaModel


class TranscriptionModel(Base):
    """Transcription result ORM model"""
    __tablename__ = "transcriptions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="CASCADE"),
        unique=True,
        index=True
    )
    language: Mapped[str] = mapped_column(String, default="en")
    full_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    media: Mapped["MediaModel"] = relationship(
        "MediaModel",
        back_populates="transcription"
    )
    segments: Mapped[list["TranscriptSegmentModel"]] = relationship(
        "TranscriptSegmentModel",
        back_populates="transcription",
        cascade="all, delete-orphan",
        order_by="TranscriptSegmentModel.segment_index"
    )


class TranscriptSegmentModel(Base):
    """Transcript segment ORM model"""
    __tablename__ = "transcript_segments"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    transcription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        index=True
    )
    segment_index: Mapped[int] = mapped_column(Integer)  # Original segment ID
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    speaker: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Relationships
    transcription: Mapped["TranscriptionModel"] = relationship(
        "TranscriptionModel",
        back_populates="segments"
    )
