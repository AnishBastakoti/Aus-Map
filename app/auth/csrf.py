import hmac
import hashlib
from uuid import UUID

from app.config import settings


CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"


def _compute_token(session_id: UUID) -> str:
    """HMAC-SHA256 over the session ID, hex-encoded."""
    message = str(session_id).encode("utf-8")
    key = settings.secret_key.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def generate_csrf_token(session_id: UUID) -> str:
    """Return the CSRF token for this session, suitable for a hidden form field."""
    return _compute_token(session_id)


def verify_csrf_token(session_id: UUID, submitted: str) -> bool:
    """
    True if `submitted` matches the expected token for this session.
    Uses constant-time comparison to defeat timing attacks.
    """
    if not submitted:
        return False
    expected = _compute_token(session_id)
    # hmac.compare_digest avoids leaking string length / position info via timing
    return hmac.compare_digest(expected, submitted)