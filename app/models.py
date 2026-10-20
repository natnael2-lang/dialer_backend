from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Chosen by the user at registration, unique, immutable. This is what gets dialed.
    chatid: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    bio: Mapped[str] = mapped_column(String(280), default="")
    photo_filename: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Only a SHA-256 hash of the device token is stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Contact(Base):
    """A saved contact: owner remembers `target` under a friendly nickname."""

    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("owner_id", "target_id", name="uq_contact_owner_target"),
        Index("ix_contacts_owner_nickname", "owner_id", "nickname"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    target_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    nickname: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    target: Mapped[Profile] = relationship(foreign_keys=[target_id], lazy="joined")