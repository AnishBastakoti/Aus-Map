from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import User
from app.models.session import Session as SessionModel


# Maximum lifetime regardless of activity. Even an active user gets kicked
# out after this long and must re-login. Defence against very long-lived sessions.
ABSOLUTE_MAX_LIFETIME = timedelta(days=30)

# Signer is shared across the app. SECRET_KEY must NOT change once users are
# logged in — every cookie signed with the old key becomes invalid.
_signer = URLSafeSerializer(settings.secret_key, salt="session-cookie")


def _now() -> datetime:
    """UTC 'now' — use timezone-aware datetimes."""
    return datetime.now(timezone.utc)


def create_session(
    db: DBSession,
    user: User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Tuple[SessionModel, str]:
    """
    Create a session row for this user. Returns (session, signed_cookie_value).
    The caller puts the signed_cookie_value into the response cookie.
    """
    lifetime = timedelta(hours=settings.session_lifetime_hours)
    expires_at = _now() + lifetime

    session = SessionModel(
        user_id=user.id,
        user_agent=user_agent[:500] if user_agent else None,  # truncate, column is varchar(500)
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Sign the session ID for the cookie. Tampering will be detected on next request.
    signed = _signer.dumps(str(session.id))
    return session, signed


def get_active_user(db: DBSession, signed_cookie_value: str) -> Optional[User]:
    if not signed_cookie_value:
        return None

    # verify signature, extract session ID
    try:
        session_id_str = _signer.loads(signed_cookie_value)
        session_id = UUID(session_id_str)
    except (BadSignature, ValueError):
        # Tampered or malformed cookie. Treat as anonymous.
        return None

    # load the session and its user (one query, joined)
    session = db.get(SessionModel, session_id)
    if session is None:
        return None  # session was destroyed or never existed

    now = _now()

    # enforce expiration
    if session.expires_at <= now:
        # Hard expired. Could also clean up here, but cleanup is async (see below).
        return None

    # enforce absolute max lifetime
    if (now - session.created_at) >= ABSOLUTE_MAX_LIFETIME:
        return None

    # user must still be active
    user = session.user
    if user is None or not user.is_active:
        return None

    # slide the expiration forward
    new_expiry = now + timedelta(hours=settings.session_lifetime_hours)
    capped_expiry = min(new_expiry, session.created_at + ABSOLUTE_MAX_LIFETIME)
    session.expires_at = capped_expiry
    session.last_active_at = now
    db.commit()

    return user


def destroy_session(db: DBSession, session_id: UUID) -> None:
    """Delete a session row. Idempotent — no error if it doesn't exist."""
    db.execute(delete(SessionModel).where(SessionModel.id == session_id))
    db.commit()


def destroy_session_by_signed_cookie(db: DBSession, signed_cookie_value: str) -> None:
    """Convenience wrapper — used by logout, which has the cookie, not the raw ID."""
    if not signed_cookie_value:
        return
    try:
        session_id_str = _signer.loads(signed_cookie_value)
        session_id = UUID(session_id_str)
    except (BadSignature, ValueError):
        return  # bad cookie, nothing to do
    destroy_session(db, session_id)


def cleanup_expired_sessions(db: DBSession) -> int:
    """
    Delete all expired sessions. Returns number deleted.
    Run periodically (cron, scheduled task) to keep the table small.
    """
    result = db.execute(
        delete(SessionModel).where(SessionModel.expires_at < _now())
    )
    db.commit()
    return result.rowcount or 0