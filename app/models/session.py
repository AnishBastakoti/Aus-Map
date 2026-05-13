from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    # The session ID. UUID, random, unguessable.
    # This value goes into the browser cookie.
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Which user this session belongs to.
    # ondelete="CASCADE" — if a user IS deleted (rare), drop their sessions too.
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # we'll often query "all sessions for user X"
    )

    # Convenience back-reference — `session.user` returns the User object.
    user: Mapped["User"] = relationship("User", lazy="joined")  # noqa: F821

    # Audit / device tracking. Not critical, but useful for "view active sessions"
    # screens and for spotting hijacked sessions ("why is my account logged in from Brazil?").
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,  # we'll periodically delete expired sessions
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} expires_at={self.expires_at}>"