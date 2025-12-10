"""
SQLAlchemy ORM model for Password_hashes table
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


class PasswordHashModel(Base):
    """Password hash ORM model"""
    __tablename__ = "password_hashes"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True
    )
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="password_hash"
    )
