from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.services.users import get_user_by_email
from app.auth.passwords import verify_password
from app.auth.sessions import (
    create_session,
    destroy_session_by_signed_cookie,
)
from app.auth.csrf import generate_csrf_token, verify_csrf_token
from app.utils.templating import template_globals

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract user-agent and IP for the session audit fields."""
    ua = request.headers.get("user-agent")
    # request.client.host is the IP. In production behind a proxy, you'd read
    # X-Forwarded-For instead — we'll handle that during deployment.
    ip = request.client.host if request.client else None
    return ua, ip


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request) -> HTMLResponse:
    """Show the login form. Anonymous users only — log others in straight to /."""
    if request.state.user is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # No session yet → no CSRF token possible yet → token will be issued post-login.
    # For the login form itself, we use a special "pre-session" CSRF approach:
    # the form posts without a token, and we rely on SameSite=Lax cookies + the
    # password itself being the proof of identity. Most frameworks handle login
    # this way — login is the one form that can't have a session-bound CSRF token,
    # because there's no session yet.
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context=template_globals(request) | {"email": "", "error": ""},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Process a login submission."""
    # If already logged in, just bounce home
    if request.state.user is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # We deliberately use the same error message for both "no such user" and
    # "wrong password" — never reveal which one was wrong. Otherwise an attacker
    # can enumerate which emails are registered.
    GENERIC_ERROR = "Invalid email or password."

    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return _render_login_with_error(request, email, GENERIC_ERROR)

    if not verify_password(user.password_hash, password):
        # Real production would also: increment user.failed_login_attempts,
        # lock account after N failures, log the attempt. We'll add that polish later.
        return _render_login_with_error(request, email, GENERIC_ERROR)

    # Success — create session and set cookie
    user_agent, ip_address = _client_info(request)
    _, signed_cookie = create_session(db, user, user_agent=user_agent, ip_address=ip_address)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=signed_cookie,
        max_age=int(timedelta(hours=settings.session_lifetime_hours).total_seconds()),
        httponly=True,           # JavaScript can't read it (prevents XSS theft)
        secure=(settings.app_env != "development"),  # HTTPS only in production
        samesite="lax",          # Sent on top-level navigation, not on cross-site POSTs
    )
    return response


@router.post("/logout")
async def logout(
    request: Request,
    csrf_token: str = Form(""),
    db: DBSession = Depends(get_db),
):
    """Destroy the session and clear the cookie. CSRF-protected."""
    # CSRF check: the submitted token must match what we'd expect for this session
    user = request.state.user
    if user is not None:
        # Find the session ID from the cookie (signed)
        cookie_value = request.cookies.get(settings.session_cookie_name, "")
        # We need the raw session_id to validate CSRF. Easiest: recompute and compare.
        # Since the middleware already loaded the user, we know the cookie is valid.
        # We'll grab the session ID by re-decoding the cookie.
        from itsdangerous import URLSafeSerializer
        from uuid import UUID
        signer = URLSafeSerializer(settings.secret_key, salt="session-cookie")
        try:
            session_id = UUID(signer.loads(cookie_value))
            if not verify_csrf_token(session_id, csrf_token):
                # Bad token — refuse the logout. Returning 403 is correct here.
                return HTMLResponse("CSRF validation failed", status_code=403)
        except Exception:
            pass

        destroy_session_by_signed_cookie(db, cookie_value)

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=settings.session_cookie_name)
    return response


def _render_login_with_error(request: Request, email: str, error: str) -> HTMLResponse:
    """Helper to re-render the login form with an error and the email pre-filled."""
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        status_code=status.HTTP_400_BAD_REQUEST,
        context=template_globals(request) | {"email": email, "error": error},
    )