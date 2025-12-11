"""
SQLAlchemy ORM model for Clips table
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .media_model import MediaModel


class ClipModel(Base):
    """Generated clip ORM model"""
    __tablename__ = "clips"
    
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
    platform: Mapped[str] = mapped_column(String)  # instagram_reels, tiktok, etc.
    file_path: Mapped[str] = mapped_column(String)
    duration: Mapped[float] = mapped_column(Float)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    has_captions: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    media: Mapped["MediaModel"] = relationship(
        "MediaModel",
        back_populates="clips"
    )


