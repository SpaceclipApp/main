"""
SQLAlchemy ORM model for Highlights table
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .media_model import MediaModel


class HighlightModel(Base):
    """Highlight/clip suggestion ORM model"""
    __tablename__ = "highlights"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="CASCADE"),
        index=True
    )
    highlight_id: Mapped[str] = mapped_column(String)  # Original string ID from AI
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    transcript_segment_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    media: Mapped["MediaModel"] = relationship(
        "MediaModel",
        back_populates="highlights"
    )
