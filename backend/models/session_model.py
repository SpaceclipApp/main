"""
SQLAlchemy ORM model for Sessions table
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .user_model import UserModel


class SessionModel(Base):
    """User session ORM model"""
    __tablename__ = "sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column()
    
    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="sessions"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_sessions_token", "token"),
        Index("idx_sessions_user_id", "user_id"),
    )

