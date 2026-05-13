from uuid import UUID
from fastapi import Request
from itsdangerous import URLSafeSerializer

from app.config import settings
from app.auth.csrf import generate_csrf_token


def template_globals(request: Request) -> dict:
    """Returns variables every template needs: app_name, user, csrf_token."""
    user = getattr(request.state, "user", None)
    csrf_token = ""
    if user is not None:
        cookie_value = request.cookies.get(settings.session_cookie_name, "")
        try:
            signer = URLSafeSerializer(settings.secret_key, salt="session-cookie")
            session_id = UUID(signer.loads(cookie_value))
            csrf_token = generate_csrf_token(session_id)
        except Exception:
            csrf_token = ""
    return {
        "app_name": settings.app_name,
        "user": user,
        "csrf_token": csrf_token,
    }