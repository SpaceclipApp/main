"""
SQLAlchemy ORM model for Users table
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from .database import Base

if TYPE_CHECKING:
    from .password_model import PasswordHashModel
    from .session_model import SessionModel
    from .project_model import ProjectModel


class UserModel(Base):
    """User account ORM model"""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String, default="email")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    password_hash: Mapped["PasswordHashModel"] = relationship(
        "PasswordHashModel",
        back_populates="user",
        uselist=False
    )
    sessions: Mapped[list["SessionModel"]] = relationship(
        "SessionModel",
        back_populates="user"
    )
    projects: Mapped[list["ProjectModel"]] = relationship(
        "ProjectModel",
        back_populates="user"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_wallet_address", "wallet_address"),
    )


