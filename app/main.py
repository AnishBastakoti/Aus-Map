from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer

from app.config import settings
from app.auth.middleware import AuthMiddleware
from app.auth.csrf import generate_csrf_token
from app.routers import auth as auth_router
from app.utils.templating import template_globals

# Where this file lives on disk — used to find templates and static folders
BASE_DIR = Path(__file__).resolve().parent

# Create the FastAPI app. The title appears in the auto-generated /docs page.
app = FastAPI(
    title=settings.app_name,
    debug=(settings.app_env == "development"),
)

# Custom authentication middleware — runs on every request, sets request.state.user
app.add_middleware(AuthMiddleware)

# Mount the auth routes (GET /login, POST /login, POST /logout)
app.include_router(auth_router.router)

# Serve static files at /static/...
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

# Jinja2 templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _template_globals(request: Request) -> dict:
    """
    Returns the dict of template variables every page needs:
    app name, current user (or None), and CSRF token (or '' if anonymous).

    Call this in every route that renders a template, and merge any
    page-specific context on top with the `|` operator.
    """
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Homepage. Shows logged-in state if user has a valid session."""
    if request.state.user is None:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=template_globals(request),
    )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint. Used to verify the app is up."""
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}