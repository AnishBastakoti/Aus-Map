from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Email is the login identifier. unique=True means the database itself
    # rejects duplicates — defence even if app-level checks fail.
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,  # we look up users by email on every login — index for speed
    )

    # The Argon2 hash, NOT the plaintext password.
    # 255 chars is plenty — Argon2 hashes are ~95-100 chars.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Display name. Nullable 
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Soft-disable — referential integrity in
    # the audit log depends on them existing forever.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Brute-force protection state. Reset on successful login.
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Audit / tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # database sets this on INSERT
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        # Useful for printing in the terminal / debugger.
        return f"<User id={self.id} email={self.email!r} active={self.is_active}>"