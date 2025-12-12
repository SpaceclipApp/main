"""
SQLAlchemy ORM model for Media table
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .project_model import ProjectModel
    from .transcription_model import TranscriptionModel
    from .highlight_model import HighlightModel
    from .clip_model import ClipModel


class MediaModel(Base):
    """Media file ORM model"""
    __tablename__ = "media"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # File info
    filename: Mapped[str] = mapped_column(String)
    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str] = mapped_column(String)
    thumbnail_path: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Media metadata
    media_type: Mapped[str] = mapped_column(String)  # "video" or "audio"
    source_type: Mapped[str] = mapped_column(String)  # "upload", "youtube", "x_space", "url"
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Processing state
    status: Mapped[str] = mapped_column(String, default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project: Mapped[Optional["ProjectModel"]] = relationship(
        "ProjectModel",
        back_populates="media"
    )
    transcription: Mapped[Optional["TranscriptionModel"]] = relationship(
        "TranscriptionModel",
        back_populates="media",
        uselist=False,
        cascade="all, delete-orphan"
    )
    highlights: Mapped[list["HighlightModel"]] = relationship(
        "HighlightModel",
        back_populates="media",
        cascade="all, delete-orphan"
    )
    clips: Mapped[list["ClipModel"]] = relationship(
        "ClipModel",
        back_populates="media",
        cascade="all, delete-orphan"
    )



