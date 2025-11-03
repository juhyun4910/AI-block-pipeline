from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="AI Block Pipeline Mockup")

templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the drag-and-drop pipeline builder mockup."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/project-overview", response_class=HTMLResponse)
async def project_overview(request: Request) -> HTMLResponse:
    """Render the detailed project overview page."""
    return templates.TemplateResponse("project_overview.html", {"request": request})
