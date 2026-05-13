from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.auth.sessions import get_active_user
from app.config import settings
from app.database import SessionLocal


class AuthMiddleware(BaseHTTPMiddleware):
    """
    For every request:
      Read the session cookie (if present)
      Look up the user
      Attach user (or None) to request.state.user
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Default: no user
        request.state.user = None

        # Try to load a user from the session cookie
        cookie_value = request.cookies.get(settings.session_cookie_name)
        if cookie_value:
            db = SessionLocal()
            try:
                user = get_active_user(db, cookie_value)
                request.state.user = user
            finally:
                db.close()

        # Continue down the chain
        response = await call_next(request)

        # Add security headers to the response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"

        return response