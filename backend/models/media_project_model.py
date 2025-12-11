"""
SQLAlchemy ORM model for Media_projects table
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .project_model import ProjectModel


class MediaProjectModel(Base):
    """Media-Project association ORM model"""
    __tablename__ = "media_projects"
    
    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE")
    )
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel",
        back_populates="media_projects"
    )


