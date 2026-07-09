"""SQLAlchemy models for the multi-tenant user registry."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256))
    email: Mapped[str | None] = mapped_column(String(256))
    wiw_id: Mapped[str | None] = mapped_column(String(128))
    container_uid: Mapped[int | None] = mapped_column(default=None)
    roles: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    responsibilities: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    identities: Mapped[list["IMIdentity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profiles: Mapped[list["UserProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class IMIdentity(Base):
    __tablename__ = "im_identities"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="identities")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_name", name="uq_user_profile"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    provisioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="profiles")
