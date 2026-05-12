from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings


# Where this file lives on disk — used to find templates and static folders
BASE_DIR = Path(__file__).resolve().parent

# Create the FastAPI app. The title appears in the auto-generated /docs page.
app = FastAPI(
    title=settings.app_name,
    debug=(settings.app_env == "development"),
)

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


@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint. Returns simple JSON.
    Used to verify the app is up.
    """
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}