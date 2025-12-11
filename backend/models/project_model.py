"""
SQLAlchemy ORM model for Projects table
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .user_model import UserModel
    from .media_project_model import MediaProjectModel
    from .media_model import MediaModel


class ProjectModel(Base):
    """Project ORM model"""
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="projects"
    )
    media_projects: Mapped[list["MediaProjectModel"]] = relationship(
        "MediaProjectModel",
        back_populates="project"
    )
    media: Mapped[list["MediaModel"]] = relationship(
        "MediaModel",
        back_populates="project"
    )
