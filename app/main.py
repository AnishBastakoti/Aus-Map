from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.auth.middleware import AuthMiddleware
from app.routers import auth as auth_router


# Where this file lives on disk — used to find templates and static folders
BASE_DIR = Path(__file__).resolve().parent

# Create the FastAPI app. The title appears in the auto-generated /docs page.
app = FastAPI(
    title=settings.app_name,
    debug=(settings.app_env == "development"),
)

# Add our custom authentication middleware to the app. This will run on every request.
app.add_middleware(AuthMiddleware)

#routes
app.include_router(auth_router.router)

# Serve files from app/static/ at the URL prefix /static
# So app/static/css/app.css becomes available at /static/css/app.css
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

# Jinja2 templates 
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"app_name": settings.app_name},
    )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_template_globals(request),
    )


def _template_globals(request: Request) -> dict:
    """Per-request template variables available in every template."""
    user = getattr(request.state, "user", None)
    csrf_token = ""
    if user is not None:
        # Reconstruct CSRF token from current session
        from itsdangerous import URLSafeSerializer
        from uuid import UUID
        from app.auth.csrf import generate_csrf_token
        cookie_value = request.cookies.get(settings.session_cookie_name, "")
        try:
            signer = URLSafeSerializer(settings.secret_key, salt="session-cookie")
            session_id = UUID(signer.loads(cookie_value))
            csrf_token = generate_csrf_token(session_id)
        except Exception:
            csrf_token = ""
    return {"user": user, "csrf_token": csrf_token, "app_name": settings.app_name}

@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint. Returns simple JSON.
    Used to verify the app is up.
    """
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}